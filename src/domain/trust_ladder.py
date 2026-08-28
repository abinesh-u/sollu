from google.cloud import firestore
from src.domain.logger import log_event

class TrustLadderEngine:
    AUTO_EXECUTE_THRESHOLD = 3

    def __init__(self, db: firestore.Client):
        self.db = db

    def get_status_for_task(self, task_class: str, correlation_id: str) -> str:
        """Determines the status of a new task based on current trust ladder state."""
        ladder_ref = self.db.collection("trust_ladder").document(task_class)
        ladder_doc = ladder_ref.get()
        approvals = ladder_doc.to_dict().get("approvals", 0) if ladder_doc.exists else 0
        
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
        
        # Read old state for logging
        old_doc = ladder_ref.get()
        old_approvals = old_doc.to_dict().get("approvals", 0) if old_doc.exists else 0
        
        ladder_ref.set({"approvals": firestore.Increment(1)}, merge=True)
        
        # Check if this increment pushed it across the threshold to log promotion event
        updated_ladder = ladder_ref.get().to_dict()
        new_approvals = updated_ladder.get("approvals", 0)
        
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
        # Read old state for logging
        ladder_ref = self.db.collection("trust_ladder").document(task_class)
        old_doc = ladder_ref.get()
        old_approvals = old_doc.to_dict().get("approvals", 0) if old_doc.exists else 0
        
        ladder_ref.set({"approvals": 0}, merge=True)
        
        if old_approvals >= self.AUTO_EXECUTE_THRESHOLD:
            log_event(correlation_id, "demotion",
                task_class=task_class,
                old_state="auto_approved",
                new_state="pending_approval",
                trigger="user_rejected_auto_task"
            )
