"""HTTP routing adapter — deliberately shallow.

Translates HTTP requests into domain calls on TaskOrchestrator and
TaskRepository. No Firestore field names, no trust-ladder logic, no executor
dispatch. Those live behind the orchestrator seam.
"""
import os
import uuid
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Header, Depends, BackgroundTasks
from fastapi.responses import HTMLResponse, Response, FileResponse
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore
from dotenv import dotenv_values

from src.domain.parser import GeminiAudioParser
from src.domain.trust_ladder import TrustLadderEngine
from src.domain.orchestrator import TaskOrchestrator
from src.domain.task_repo import TaskRepository
from src.domain.logger import log_event
from src.domain.executor_runner import run_auto_approved
from src.domain import speaker
from src.executors.registry import KNOWN_CLASSES, describe
from src.executors.gemini_executors import warm_up
from src.agent import run_voice_agent
from src.mcp_server import mcp

cfg = dotenv_values(".env")
db = firestore.Client(project=cfg.get("GOOGLE_CLOUD_PROJECT"))

repo = TaskRepository(db)
orchestrator = TaskOrchestrator(repo, GeminiAudioParser())

app = FastAPI(title="Voice Agent API")

# Add the internal MCP Server SSE endpoints (/sse and /messages)
app.routes.extend(mcp.sse_app().routes)

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
        # Route through the ADK agent (src/agent.py) rather than calling the
        # orchestrator directly — this is the Google Agent Framework mandatory,
        # and it must sit on the live request path, not just exist in the repo.
        tasks_data = await run_voice_agent(
            file_path, correlation_id, image_path, image_mime, audio_mime)

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

@app.delete("/api/tasks/{task_id}")
def delete_task(task_id: str):
    repo.delete(task_id)
    return {"status": "deleted"}

@app.get("/api/tasks")
def get_tasks():
    return repo.list_recent()

def _read_ladder() -> dict:
    """Approval count per class, with every known class present at zero."""
    return orchestrator.trust_engine.read_all_approvals(KNOWN_CLASSES)

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
        entry["auto"] = orchestrator.trust_engine.is_autonomous(c, approvals)
        
        # Inject the threshold directly for the frontend
        threshold = orchestrator.trust_engine._get_threshold(c)
        entry["threshold"] = threshold if threshold is not None else "never"
        
        out.append(entry)
    return out

@app.post("/api/tasks/{task_id}/approve")
def approve_task(task_id: str):
    try:
        return orchestrator.approve(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

@app.post("/api/tasks/{task_id}/reject")
def reject_task(task_id: str):
    try:
        return orchestrator.reject(task_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Task not found")

@app.post("/api/cron/deferred")
def process_deferred_tasks(_=Depends(verify_cron_secret)):
    return orchestrator.evaluate_deferred()

from google_auth_oauthlib.flow import Flow
from fastapi.responses import RedirectResponse
from fastapi import Request
import os

OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/gmail.compose',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/tasks'
]

# Workaround for Google sometimes returning slightly different scopes
os.environ["OAUTHLIB_RELAX_TOKEN_SCOPE"] = "1"

def get_oauth_flow(request: Request):
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.url.netloc)
    redirect_uri = os.environ.get("OAUTH_REDIRECT_URI") or f"{scheme}://{host}/oauth/callback"
    
    client_config = {
        "web": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "project_id": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": os.environ.get("GOOGLE_CLIENT_SECRET", "")
        }
    }
    
    return Flow.from_client_config(
        client_config,
        scopes=OAUTH_SCOPES,
        redirect_uri=redirect_uri
    )

@app.get("/oauth/start")
def oauth_start(request: Request, password: str = None):
    # Gate setup so random visitors don't override your credentials
    if os.environ.get("SETUP_ENABLED", "true").lower() != "true":
        raise HTTPException(status_code=403, detail="Setup is disabled")
        
    expected_password = os.environ.get("SETUP_PASSWORD")
    if expected_password and password != expected_password:
        raise HTTPException(status_code=401, detail="Unauthorized setup access")

    if not os.environ.get("GOOGLE_CLIENT_ID") or not os.environ.get("GOOGLE_CLIENT_SECRET"):
        raise HTTPException(status_code=500, detail="Missing GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET")
        
    flow = get_oauth_flow(request)
    auth_url, state = flow.authorization_url(
        access_type="offline", prompt="consent", include_granted_scopes="true"
    )
    
    resp = RedirectResponse(auth_url)
    is_https = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
    resp.set_cookie("oauth_state", state, httponly=True, secure=is_https, samesite="lax", max_age=600)
    
    # Store PKCE code_verifier generated by authorization_url
    if hasattr(flow, "code_verifier"):
        resp.set_cookie("oauth_cv", flow.code_verifier, httponly=True, secure=is_https, samesite="lax", max_age=600)
        
    return resp

@app.get("/oauth/callback")
def oauth_callback(request: Request, code: str, state: str):
    if state != request.cookies.get("oauth_state"):
        raise HTTPException(status_code=400, detail="State mismatch. Please try again.")
        
    flow = get_oauth_flow(request)
    
    # Restore PKCE code_verifier
    cv = request.cookies.get("oauth_cv")
    if cv:
        flow.code_verifier = cv
        
    flow.fetch_token(code=code)
    creds = flow.credentials
    
    if creds.refresh_token:
        db.collection('oauth_tokens').document('default_user').set({
            'refresh_token': creds.refresh_token,
            'updated_at': firestore.SERVER_TIMESTAMP
        }, merge=True)
        return {"status": "ok", "message": "Successfully authenticated! You can close this window."}
    else:
        return {"status": "warning", "message": "No refresh token received. You may need to revoke access and try again."}

# Mount static assets from built frontend if available
if os.path.exists("frontend/dist/assets"):
    app.mount("/assets", StaticFiles(directory="frontend/dist/assets"), name="assets")

@app.get("/favicon.svg")
def get_favicon():
    if os.path.exists("frontend/dist/favicon.svg"):
        return FileResponse("frontend/dist/favicon.svg", media_type="image/svg+xml")
    if os.path.exists("frontend/public/favicon.svg"):
        return FileResponse("frontend/public/favicon.svg", media_type="image/svg+xml")
    raise HTTPException(status_code=404, detail="Favicon not found")

@app.get("/", response_class=HTMLResponse)
@app.get("/kit", response_class=HTMLResponse)
def get_ui():
    if os.path.exists("frontend/dist/index.html"):
        with open("frontend/dist/index.html", "r") as f:
            return f.read()
    raise HTTPException(
        status_code=404,
        detail="Frontend not built. Run 'npm run build' in frontend/ to generate dist/index.html"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
