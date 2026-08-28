from google.cloud import firestore
from datetime import datetime, timezone
import time
from src.domain.parser import GeminiAudioParser
from src.domain.trust_ladder import TrustLadderEngine
from src.domain.logger import log_event

# Verified against gemini-3.5-flash: audio/webm, audio/ogg, audio/mp4 and
# audio/wav all parse, with or without a ";codecs=opus" suffix. video/webm is
# rejected with a 400 -- and MediaRecorder blobs are easy to label that way, so
# the video/* prefix is rewritten rather than passed through.
_EXT_MIME = {
    ".wav": "audio/wav",
    ".mp3": "audio/mp3",
    ".m4a": "audio/mp4",
    ".ogg": "audio/ogg",
    ".webm": "audio/webm",
}


def normalise_audio_mime(declared: str, path: str) -> str:
    """Prefer what the upload declared; fall back to the extension."""
    if declared:
        m = declared.strip()
        if m.startswith("video/"):
            m = "audio/" + m.split("/", 1)[1]
        if m.startswith("audio/"):
            return m
    for ext, mime in _EXT_MIME.items():
        if path.lower().endswith(ext):
            return mime
    return "audio/wav"


class TaskOrchestrator:
    def __init__(self, db: firestore.Client, parser: GeminiAudioParser):
        self.db = db
        self.parser = parser
        self.trust_engine = TrustLadderEngine(db)

    def process_voice_note(self, audio_path: str, correlation_id: str,
                           image_path: str = None, image_mime: str = None,
                           audio_mime: str = None) -> dict:
        """End-to-end pipeline: read audio, parse tasks, apply trust ladder, persist.

        An optional image is sent in the same Gemini request as the audio.
        `audio_mime` comes from the upload; a browser recording is not a .wav or
        an .mp3 and must not be guessed at from its filename.
        """
        mime = normalise_audio_mime(audio_mime, audio_path)
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        image_bytes = None
        if image_path:
            with open(image_path, "rb") as f:
                image_bytes = f.read()

        start_time = time.time()
        # 1. Parse using Gemini
        tasks_list, token_usage = self.parser.parse_audio(
            audio_bytes, mime, image_bytes=image_bytes, image_mime=image_mime)
        latency = round(time.time() - start_time, 2)

        log_event(correlation_id, "tasks extracted",
            count=len(tasks_list),
            token_usage=token_usage,
            latency_seconds=latency,
            with_image=bool(image_bytes)
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
                # Only meaningful when an image rode along; audio-only notes
                # record "audio" with no evidence.
                "source": task_item.get("source", "audio"),
                "evidence": task_item.get("evidence") or None,
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
