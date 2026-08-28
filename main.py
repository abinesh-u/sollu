import os
import json
import asyncio
import uuid
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, Response
from google.cloud import firestore
from dotenv import dotenv_values
from datetime import datetime, timezone

from src.domain.parser import GeminiAudioParser
from src.domain.trust_ladder import TrustLadderEngine
from src.domain.orchestrator import TaskOrchestrator
from src.domain.logger import log_event
from src.domain.evaluator import ConditionEvaluator
from src.executors.registry import KNOWN_CLASSES, describe
from src.executors.gemini_executors import warm_up
from src.domain.executor_runner import run_for_task, run_auto_approved
from src.domain import speaker

cfg = dotenv_values(".env")
db = firestore.Client(project=cfg.get("GOOGLE_CLOUD_PROJECT"))

trust_engine = TrustLadderEngine(db)
orchestrator = TaskOrchestrator(db, GeminiAudioParser())
evaluator = ConditionEvaluator()

app = FastAPI(title="Voice Agent API")

def verify_cron_secret(x_cron_secret: str = Header(None)):
    expected = cfg.get("CRON_SECRET")
    if not expected or x_cron_secret != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return x_cron_secret

@app.on_event("startup")
def _warm_clients():
    """Build the executor client before the first request needs it.

    Executors run under a wall-clock deadline, so connection setup must not
    happen inside one on a cold instance. Never fatal — a failure here just
    means the first executor pays the cost it would have paid anyway.
    """
    try:
        warm_up()
        log_event("startup", "executor client warmed")
    except Exception as e:
        log_event("startup", "executor warm-up failed", error=f"{type(e).__name__}: {e}"[:200])

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/tasks")
async def process_audio(background: BackgroundTasks, file: UploadFile = File(...),
                        image: UploadFile = File(None)):
    correlation_id = str(uuid.uuid4())
    # Save the uploaded file temporarily. The name is generated, not taken from
    # the upload: a MediaRecorder blob has no meaningful filename, and an
    # attacker-supplied one has no business reaching the filesystem.
    audio_mime = file.content_type
    ext = os.path.splitext(file.filename or "")[1][:8] or ".audio"
    file_path = f"/tmp/{correlation_id}{ext}"
    with open(file_path, "wb") as f:
        file_bytes = await file.read()
        f.write(file_bytes)

    # Optional image, sent in the same Gemini request as the audio.
    image_path = None
    image_mime = None
    if image is not None and image.filename:
        image_mime = image.content_type or "image/jpeg"
        image_path = f"/tmp/{correlation_id}-image"
        with open(image_path, "wb") as f:
            f.write(await image.read())

    log_event(correlation_id, "note received", size_bytes=len(file_bytes),
              mime=audio_mime, with_image=bool(image_path))

    try:
        # Run orchestrator synchronously in thread pool
        tasks_data = await asyncio.to_thread(
            orchestrator.process_voice_note, file_path, correlation_id,
            image_path, image_mime, audio_mime)

        # Auto-approved tasks execute in the background: a grounded research call
        # is ~19s and runs per task, so executing inline would make this response
        # scale with how many classes have earned autonomy. The orchestrator has
        # already written execution_status="executing" on each doc, so the card
        # shows work in progress rather than a blank — no extra write here.
        queued = [
            {"id": t["id"], "data": t, "correlation_id": correlation_id}
            for t in tasks_data.get("tasks", [])
            if t.get("status") == "auto_approved"
        ]
        if queued:
            log_event(correlation_id, "execution queued", count=len(queued),
                      task_ids=[q["id"] for q in queued])
            background.add_task(run_auto_approved, db, queued)

        return tasks_data
    except Exception as e:
        return {"error": "Failed to process audio", "raw": str(e)}
    finally:
        for p in (file_path, image_path):
            if p and os.path.exists(p):
                os.remove(p)

@app.post("/api/speak")
def speak_summary(payload: dict):
    """Voice an already-computed triage result. Secondary model, output only.

    Given counts the caller already has — this re-derives nothing, and neither
    the audio nor the transcript nor the task text reaches the TTS model. On any
    failure it returns 204 and the UI keeps its text summary; nothing here can
    affect upload, triage, execution, or the ladder.
    """
    correlation_id = payload.get("correlation_id", "speak")
    text = speaker.build_summary(
        total=int(payload.get("total", 0)),
        pending=int(payload.get("pending", 0)),
        watching=int(payload.get("watching", 0)),
        auto_classes=payload.get("auto_classes") or [],
    )
    audio = speaker.speak(text, correlation_id)
    if not audio:
        return Response(status_code=204)
    return Response(content=audio, media_type="audio/wav",
                    headers={"X-Spoken-Text": text})

@app.get("/api/tasks")
def get_tasks():
    tasks = []
    # Fetch tasks, ordered by created_at descending
    docs = db.collection("tasks").order_by("created_at", direction=firestore.Query.DESCENDING).limit(50).stream()
    for doc in docs:
        t = doc.to_dict()
        t["id"] = doc.id
        if "created_at" in t and hasattr(t["created_at"], "isoformat"):
            t["created_at"] = t["created_at"].isoformat()
        tasks.append(t)
    return tasks

def _read_ladder() -> dict:
    """Approval count per class, with every known class present at zero.

    Single source for both /api/trust_ladder and /api/classes so the two routes
    cannot disagree.
    """
    ladder = {c: 0 for c in KNOWN_CLASSES}
    for doc in db.collection("trust_ladder").stream():
        ladder[doc.id] = doc.to_dict().get("approvals", 0)
    return ladder

@app.get("/api/trust_ladder")
def get_trust_ladder():
    return _read_ladder()

@app.get("/api/classes")
def get_classes():
    """Every task class with its executor status and current autonomy."""
    ladder = _read_ladder()
    out = []
    for c in KNOWN_CLASSES:
        entry = describe(c)
        approvals = ladder.get(c, 0)
        entry["approvals"] = approvals
        entry["auto"] = approvals >= TrustLadderEngine.AUTO_EXECUTE_THRESHOLD
        out.append(entry)
    return out

@app.post("/api/tasks/{task_id}/approve")
def approve_task(task_id: str):
    # Using task_id as correlation_id for approve/reject actions since they happen out of band
    correlation_id = task_id 
    
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")
    
    data = doc.to_dict()
    execution = None
    if data.get("status") == "pending_approval":
        # Update task status
        doc_ref.update({"status": "approved"})
        # Increment trust ladder
        task_class = data.get("class", "other")
        trust_engine.record_approval(task_class, correlation_id)

        # Approval is what earns execution — run it now. The UI already re-polls,
        # so the extra seconds here are acceptable on the manual path.
        execution = run_for_task(db, task_id, data, data.get("correlation_id", correlation_id))

    return {"status": "ok", "execution": execution}

@app.post("/api/tasks/{task_id}/reject")
def reject_task(task_id: str):
    correlation_id = task_id
    doc_ref = db.collection("tasks").document(task_id)
    doc = doc_ref.get()
    if not doc.exists:
        raise HTTPException(status_code=404, detail="Task not found")
        
    data = doc.to_dict()
    doc_ref.update({"status": "rejected"})
    
    # If rejecting an auto-executed task, reset the ladder (demotion signal)
    if data.get("status") == "auto_approved":
        task_class = data.get("class", "other")
        trust_engine.record_demotion(task_class, correlation_id)
        
    return {"status": "ok"}

@app.post("/api/cron/deferred")
def process_deferred_tasks(_=Depends(verify_cron_secret)):
    correlation_id = str(uuid.uuid4())
    now_ts = datetime.now(timezone.utc).timestamp()
    
    # Query tasks in 'later' lane
    docs = db.collection("tasks").where("lane", "==", "later").stream()
    
    results = []
    for doc in docs:
        data = doc.to_dict()
        check_after = data.get("check_after", 0)
        
        # In-memory filter to avoid composite index requirement
        if check_after > now_ts:
            continue
            
        condition = data.get("condition", "")
        
        is_met = evaluator.evaluate(condition)
        
        if is_met:
            db.collection("tasks").document(doc.id).update({"lane": "next"})
            log_event(correlation_id, "deferred wake fired", 
                task=data.get("task"), 
                old_state="later", 
                new_state="promoted_to_next",
                trigger="condition_met"
            )
            results.append({"id": doc.id, "action": "promoted"})
        else:
            # Re-defer for another 5 minutes
            new_check_after = now_ts + (5 * 60)
            db.collection("tasks").document(doc.id).update({"check_after": new_check_after})
            log_event(correlation_id, "deferred wake fired", 
                task=data.get("task"), 
                old_state="later", 
                new_state="re-deferred",
                trigger="condition_not_met"
            )
            results.append({"id": doc.id, "action": "re-deferred"})
            
    return {"status": "ok", "processed": len(results), "results": results}

@app.get("/", response_class=HTMLResponse)
def get_ui():
    with open("src/templates/index.html", "r") as f:
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
