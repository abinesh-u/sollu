from google.cloud import firestore
from src.domain.logger import log_event

class TrustLadderEngine:
    AUTO_EXECUTE_THRESHOLD = 3

    def __init__(self, db: firestore.Client):
        self.db = db

    def _read_approvals(self, task_class: str) -> int:
        """Read the current approval count for a task class.

        Single source for the pre-operation read so record_approval and
        record_demotion cannot diverge on how they fetch existing state.
        """
        doc = self.db.collection("trust_ladder").document(task_class).get()
        return doc.to_dict().get("approvals", 0) if doc.exists else 0

    def get_status_for_task(self, task_class: str, correlation_id: str) -> str:
        """Determines the status of a new task based on current trust ladder state."""
        approvals = self._read_approvals(task_class)
        
        status = "auto_approved" if approvals >= self.AUTO_EXECUTE_THRESHOLD else "pending_approval"
        
        log_event(correlation_id, "ladder consulted", 
            task_class=task_class, 
            current_approvals=approvals, 
            threshold=self.AUTO_EXECUTE_THRESHOLD, 
            resulting_autonomy=status
        )
        return status

    def record_approval(self, task_class: str, correlation_id: str):
        """Atomically increments the approval count and handles threshold crossing."""
        ladder_ref = self.db.collection("trust_ladder").document(task_class)
        
        old_approvals = self._read_approvals(task_class)
        
        ladder_ref.set({"approvals": firestore.Increment(1)}, merge=True)
        
        # The increment is +1, so the new count is deterministic without a
        # second round-trip read.
        new_approvals = old_approvals + 1
        
        if old_approvals < self.AUTO_EXECUTE_THRESHOLD and new_approvals >= self.AUTO_EXECUTE_THRESHOLD:
            self.db.collection("promotion_events").add({
                "class": task_class,
                "timestamp": firestore.SERVER_TIMESTAMP,
                "count": self.AUTO_EXECUTE_THRESHOLD
            })
            log_event(correlation_id, "promotion",
                task_class=task_class,
                old_state="pending_approval",
                new_state="auto_approved",
                trigger="user_approved_task"
            )

    def record_demotion(self, task_class: str, correlation_id: str):
        """Demotes a task class by resetting its approval count to 0."""
        old_approvals = self._read_approvals(task_class)
        
        self.db.collection("trust_ladder").document(task_class).set(
            {"approvals": 0}, merge=True)
        
        if old_approvals >= self.AUTO_EXECUTE_THRESHOLD:
            log_event(correlation_id, "demotion",
                task_class=task_class,
                old_state="auto_approved",
                new_state="pending_approval",
                trigger="user_rejected_auto_task"
            )
