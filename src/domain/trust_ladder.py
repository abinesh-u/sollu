from google.cloud import firestore
from src.domain.logger import log_event
from src.domain.intents import get_intent, Reversibility

class TrustLadderEngine:
    AUTO_EXECUTE_THRESHOLD = 3

    def __init__(self, db: firestore.Client):
        self.db = db

    def _get_tier(self, task_class: str) -> str:
        intent = get_intent(task_class)
        return intent.reversibility.value if intent else Reversibility.NONE.value

    def _read_approvals(self, tier: str) -> int:
        """Read the current approval count for a reversibility tier.
        
        Single source for the pre-operation read so record_approval and
        record_demotion cannot diverge on how they fetch existing state.
        """
        doc = self.db.collection("trust_ladder").document(tier).get()
        return doc.to_dict().get("approvals", 0) if doc.exists else 0

    def read_all_approvals(self, known_classes: list[str]) -> dict[str, int]:
        """Approval count per class. We map the tier count back to the class for the UI."""
        ladder = {c: 0 for c in known_classes}
        tier_counts = {}
        for doc in self.db.collection("trust_ladder").stream():
            tier_counts[doc.id] = doc.to_dict().get("approvals", 0)
            
        for c in known_classes:
            tier = self._get_tier(c)
            ladder[c] = tier_counts.get(tier, 0)
        return ladder

    def is_autonomous(self, approvals: int) -> bool:
        """True if the approval count meets or exceeds the autonomy threshold."""
        return approvals >= self.AUTO_EXECUTE_THRESHOLD

    def get_status_for_task(self, task: dict, correlation_id: str) -> str:
        """Determines the status of a new task based on current trust ladder state."""
        task_class = task.get("class", "")
        tier = self._get_tier(task_class)
        approvals = self._read_approvals(tier)
        
        # Hard Rule: If the task has an unresolved recipient (requires disambiguation),
        # it strictly cannot auto-execute, regardless of earned trust.
        is_unresolved = task.get("unresolved_recipient", False)
        
        if is_unresolved:
            status = "pending_approval"
        else:
            status = "auto_approved" if approvals >= self.AUTO_EXECUTE_THRESHOLD else "pending_approval"
        
        log_event(correlation_id, "ladder consulted", 
            task_class=task_class,
            tier=tier,
            current_approvals=approvals, 
            threshold=self.AUTO_EXECUTE_THRESHOLD, 
            resulting_autonomy=status,
            unresolved_recipient=is_unresolved
        )
        return status

    def record_approval(self, task_class: str, correlation_id: str):
        """Atomically increments the approval count and handles threshold crossing for the tier."""
        tier = self._get_tier(task_class)
        ladder_ref = self.db.collection("trust_ladder").document(tier)
        
        old_approvals = self._read_approvals(tier)
        
        ladder_ref.set({"approvals": firestore.Increment(1)}, merge=True)
        
        new_approvals = old_approvals + 1
        
        if old_approvals < self.AUTO_EXECUTE_THRESHOLD and new_approvals >= self.AUTO_EXECUTE_THRESHOLD:
            self.db.collection("promotion_events").add({
                "tier": tier,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "count": self.AUTO_EXECUTE_THRESHOLD
            })
            log_event(correlation_id, "promotion",
                task_class=task_class,
                tier=tier,
                old_state="pending_approval",
                new_state="auto_approved",
                trigger="user_approved_task"
            )

    def record_demotion(self, task_class: str, correlation_id: str):
        """Demotes a tier by resetting its approval count to 0."""
        tier = self._get_tier(task_class)
        old_approvals = self._read_approvals(tier)
        
        self.db.collection("trust_ladder").document(tier).set(
            {"approvals": 0}, merge=True)
        
        if old_approvals >= self.AUTO_EXECUTE_THRESHOLD:
            log_event(correlation_id, "demotion",
                task_class=task_class,
                tier=tier,
                old_state="auto_approved",
                new_state="pending_approval",
                trigger="user_rejected_auto_task"
            )
