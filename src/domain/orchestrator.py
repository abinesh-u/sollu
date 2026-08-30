"""Full task lifecycle: ingest, approve, reject, deferred evaluation.

This is the single domain module that owns what happens to a task from creation
through completion. The HTTP layer calls one method per action and gets back a
result; it never touches Firestore, the trust ladder, or executor dispatch
directly.
"""
from datetime import datetime, timezone
import time

from google.cloud import firestore

from src.domain.evaluator import ConditionEvaluator
from src.domain.executor_runner import run_for_task
from src.domain.logger import log_event
from src.domain.parser import GeminiAudioParser
from src.domain.task_repo import TaskRepository
from src.domain.trust_ladder import TrustLadderEngine
from src.executors.base import AUTO_APPROVED, PENDING_APPROVAL

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
    def __init__(self, repo: TaskRepository, parser: GeminiAudioParser):
        self.repo = repo
        self.parser = parser
        self.trust_engine = TrustLadderEngine(repo._db)
        self._evaluator = ConditionEvaluator()

    # ── Ingest ──────────────────────────────────────────────────────────

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
            status = self.trust_engine.get_status_for_task(task_item, correlation_id)

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
            if status == AUTO_APPROVED:
                doc_data["execution_status"] = "executing"

            if task_lane == "later":
                doc_data["condition"] = condition
                # Default to 1 minute in the future for demo purposes if not specified
                doc_data["check_after"] = datetime.now(timezone.utc).timestamp() + (defer_duration_minutes * 60)

            # 3. Persist to Firestore
            _, saved = self.repo.create(doc_data)
            saved_tasks.append(saved)

        # Compute summary for client UI and spoken confirmation
        total = len(saved_tasks)
        pending = sum(1 for t in saved_tasks if t.get("status") == PENDING_APPROVAL)
        watching = sum(1 for t in saved_tasks if t.get("lane") == "later")
        auto_classes = sorted(list({t.get("class") for t in saved_tasks if t.get("status") == AUTO_APPROVED and t.get("class")}))

        summary = {
            "total": total,
            "pending": pending,
            "watching": watching,
            "auto_classes": auto_classes,
            "correlation_id": correlation_id
        }

        return {
            "tasks": saved_tasks,
            "summary": summary,
            "usage": token_usage
        }

    # ── Approval / Rejection ────────────────────────────────────────────

    def approve(self, task_id: str) -> dict:
        """Approve a task: update status, record ladder approval, execute.

        Returns the execution result dict (or None if the task was not pending).
        """
        data = self.repo.get_or_raise(task_id)
        # Read the originating note's correlation_id off the task document so the
        # whole lifecycle greps out in order, per AGENTS.md.
        correlation_id = data.get("correlation_id", task_id)

        execution = None
        if data.get("status") == "pending_approval":
            self.repo.update(task_id, {"status": "approved"})
            task_class = data.get("class", "other")
            self.trust_engine.record_approval(task_class, correlation_id)

            # Approval is what earns execution — run it now. The UI already
            # re-polls, so the extra seconds here are acceptable on the manual
            # path.
            execution = run_for_task(
                self.repo._db, task_id, data, correlation_id)

        return {"status": "ok", "execution": execution}

    def reject(self, task_id: str) -> dict:
        """Reject a task: update status, record ladder demotion if auto-approved."""
        data = self.repo.get_or_raise(task_id)
        correlation_id = data.get("correlation_id", task_id)

        self.repo.update(task_id, {"status": "rejected"})

        # If rejecting an auto-executed task, reset the ladder (demotion signal)
        if data.get("status") == AUTO_APPROVED:
            task_class = data.get("class", "other")
            self.trust_engine.record_demotion(task_class, correlation_id)

        return {"status": "ok"}

    # ── Deferred evaluation ─────────────────────────────────────────────

    def evaluate_deferred(self) -> dict:
        """Check later-lane tasks whose conditions are due.

        Returns a summary of what was promoted or re-deferred.
        """
        now_ts = datetime.now(timezone.utc).timestamp()
        ready = self.repo.list_deferred_ready(now_ts)

        results = []
        for data in ready:
            task_id = data["id"]
            # Use the task's originating correlation_id so the whole note
            # lifecycle greps out in order, per AGENTS.md.
            task_cid = data.get("correlation_id", "deferred")
            condition = data.get("condition", "")

            is_met = self._evaluator.evaluate(condition)

            if is_met:
                self.repo.update(task_id, {"lane": "next"})
                log_event(task_cid, "deferred wake fired",
                    task=data.get("task"),
                    old_state="later",
                    new_state="promoted_to_next",
                    trigger="condition_met"
                )
                results.append({"id": task_id, "action": "promoted"})
            else:
                new_check_after = now_ts + (5 * 60)
                self.repo.update(task_id, {"check_after": new_check_after})
                log_event(task_cid, "deferred wake fired",
                    task=data.get("task"),
                    old_state="later",
                    new_state="re-deferred",
                    trigger="condition_not_met"
                )
                results.append({"id": task_id, "action": "re-deferred"})

        return {"status": "ok", "processed": len(results), "results": results}
