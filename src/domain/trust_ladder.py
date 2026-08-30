import math
from google.cloud import firestore
from src.domain.logger import log_event
from src.domain.intents import get_intent, Reversibility
from src.executors.base import AUTO_APPROVED, PENDING_APPROVAL

class TrustLadderEngine:
    def __init__(self, db: firestore.Client):
        self.db = db

    def _get_threshold(self, task_class: str) -> int | None:
        """Determines the required approvals based on task risk. None = never auto-approves."""
        intent = get_intent(task_class)
        reversibility = intent.reversibility if intent else Reversibility.READ_ONLY
        
        if reversibility == Reversibility.READ_ONLY:
            return 0
        if reversibility == Reversibility.SOFT:
            return 3
        return None

    def _read_approvals(self, task_class: str) -> int:
        """Read the current approval count for a specific task class."""
        doc = self.db.collection("trust_ladder").document(task_class).get()
        return doc.to_dict().get("approvals", 0) if doc.exists else 0

    def read_all_approvals(self, known_classes: list[str]) -> dict[str, int]:
        """Approval count per class directly from Firestore."""
        ladder = {c: 0 for c in known_classes}
        for doc in self.db.collection("trust_ladder").stream():
            if doc.id in known_classes:
                ladder[doc.id] = doc.to_dict().get("approvals", 0)
        return ladder

    def is_autonomous(self, task_class: str, approvals: int) -> bool:
        """True if the approval count meets or exceeds the autonomy threshold."""
        threshold = self._get_threshold(task_class)
        return threshold is not None and approvals >= threshold

    def get_status_for_task(self, task: dict, correlation_id: str) -> str:
        """Determines the status of a new task based on current trust ladder state."""
        task_class = task.get("class", "")
        approvals = self._read_approvals(task_class)
        threshold = self._get_threshold(task_class)
        
        # Hard Rule: If the task has an unresolved recipient (requires disambiguation),
        # it strictly cannot auto-execute, regardless of earned trust.
        is_unresolved = task.get("unresolved_recipient", False)
        
        if is_unresolved:
            status = PENDING_APPROVAL
        else:
            status = AUTO_APPROVED if threshold is not None and approvals >= threshold else PENDING_APPROVAL
        
        log_event(correlation_id, "ladder consulted", 
            task_class=task_class,
            current_approvals=approvals, 
            threshold=threshold if threshold is not None else "never", 
            resulting_autonomy=status,
            unresolved_recipient=is_unresolved
        )
        return status

    def record_approval(self, task_class: str, correlation_id: str):
        """Atomically increments the approval count and handles threshold crossing."""
        ladder_ref = self.db.collection("trust_ladder").document(task_class)
        old_approvals = self._read_approvals(task_class)
        threshold = self._get_threshold(task_class)
        
        ladder_ref.set({"approvals": firestore.Increment(1)}, merge=True)
        new_approvals = old_approvals + 1
        
        if threshold is not None and old_approvals < threshold and new_approvals >= threshold:
            self.db.collection("promotion_events").add({
                "task_class": task_class,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "count": threshold
            })
            log_event(correlation_id, "promotion",
                task_class=task_class,
                old_state="pending_approval",
                new_state="auto_approved",
                trigger="user_approved_task"
            )

    def record_demotion(self, task_class: str, correlation_id: str):
        """Demotes a task class by resetting its approval count to 0."""
        threshold = self._get_threshold(task_class)
        
        # READ_ONLY tasks (threshold 0) cannot be demoted.
        if threshold == 0:
            return
            
        old_approvals = self._read_approvals(task_class)
        
        self.db.collection("trust_ladder").document(task_class).set(
            {"approvals": 0}, merge=True)
        
        # Only log demotion if it was previously auto-approved
        if threshold is not None and old_approvals >= threshold:
            log_event(correlation_id, "demotion",
                task_class=task_class,
                old_state="auto_approved",
                new_state="pending_approval",
                trigger="user_rejected_auto_task"
            )
