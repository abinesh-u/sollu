import os
import json
import asyncio
from fastapi import FastAPI, UploadFile, File
from src.agent import agent
from google.adk import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

app = FastAPI(title="Voice Agent API")

# Re-usable runner
runner = Runner(agent=agent, session_service=InMemorySessionService(), app_name="voice-agent-app", auto_create_session=True)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/tasks")
async def process_audio(file: UploadFile = File(...)):
    # Save the uploaded file temporarily
    file_path = f"/tmp/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
        
    try:
        new_message = types.Content(parts=[types.Part.from_text(text=file_path)], role="user")
        
        response_text = ""
        # Synchronously iterate over the runner, but it's an async route so we might block.
        # Let's run it in to_thread since runner.run is sync.
        def run_agent():
            res = ""
            for event in runner.run(user_id="api_user", session_id="api_session", new_message=new_message):
                if hasattr(event, "message"):
                    if hasattr(event.message, "parts") and event.message.parts:
                        res += event.message.parts[0].text
                    elif isinstance(event.message, str):
                        res += event.message
            return res
            
        response_text = await asyncio.to_thread(run_agent)
        
        try:
            tasks_data = json.loads(response_text)
            return tasks_data
        except json.JSONDecodeError:
            return {"error": "Failed to decode agent response", "raw": response_text}
            
    finally:
        # Clean up
        if os.path.exists(file_path):
            os.remove(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
