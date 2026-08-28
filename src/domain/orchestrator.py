from google.cloud import firestore
from datetime import datetime, timezone
import time
from src.domain.parser import GeminiAudioParser
from src.domain.trust_ladder import TrustLadderEngine
from src.domain.logger import log_event

class TaskOrchestrator:
    def __init__(self, db: firestore.Client, parser: GeminiAudioParser):
        self.db = db
        self.parser = parser
        self.trust_engine = TrustLadderEngine(db)

    def process_voice_note(self, audio_path: str, correlation_id: str) -> dict:
        """End-to-end pipeline: read audio, parse tasks, apply trust ladder, persist."""
        mime = "audio/wav" if audio_path.endswith(".wav") else "audio/mp3"
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        start_time = time.time()
        # 1. Parse using Gemini
        tasks_list, token_usage = self.parser.parse_audio(audio_bytes, mime)
        latency = round(time.time() - start_time, 2)
        
        log_event(correlation_id, "tasks extracted", 
            count=len(tasks_list), 
            token_usage=token_usage, 
            latency_seconds=latency
        )
        
        saved_tasks = []
        for task_item in tasks_list:
            task_class = task_item.get("class", "other")
            task_text = task_item.get("task")
            task_lane = task_item.get("lane")
            condition = task_item.get("condition")
            defer_duration_minutes = task_item.get("defer_duration_minutes", 1)
            
            log_event(correlation_id, "triage decision", 
                task=task_text, 
                task_class=task_class, 
                lane=task_lane
            )
            
            # 2. Get status from Trust Ladder Engine
            status = self.trust_engine.get_status_for_task(task_class, correlation_id)
            
            doc_data = {
                "task": task_text,
                "lane": task_lane,
                "class": task_class,
                "status": status,
                "created_at": firestore.SERVER_TIMESTAMP,
                "usage": token_usage,
                "correlation_id": correlation_id
            }
            
            # Auto-approved tasks execute in the background straight after this
            # response. Stamping the state in the same write the doc is created
            # with costs nothing and means the doc is never observable as
            # auto-approved with no execution state under it.
            if status == "auto_approved":
                doc_data["execution_status"] = "executing"

            if task_lane == "later":
                doc_data["condition"] = condition
                # Default to 1 minute in the future for demo purposes if not specified
                doc_data["check_after"] = datetime.now(timezone.utc).timestamp() + (defer_duration_minutes * 60)
            
            # 3. Persist to Firestore
            _, doc_ref = self.db.collection("tasks").add(doc_data)
            doc_data["id"] = doc_ref.id
            doc_data["created_at"] = datetime.now(timezone.utc).isoformat()
            saved_tasks.append(doc_data)
            
        return {
            "tasks": saved_tasks,
            "usage": token_usage
        }
