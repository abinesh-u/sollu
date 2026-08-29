import json
import uuid
from google.cloud import firestore
from dotenv import dotenv_values
from google.adk.agents.base_agent import BaseAgent
from google.adk.events import Event
from google.adk.tools import FunctionTool
import asyncio
import re

from src.domain.parser import GeminiAudioParser
from src.domain.orchestrator import TaskOrchestrator
from src.domain.task_repo import TaskRepository

cfg = dotenv_values(".env")
db = firestore.Client(project=cfg.get("GOOGLE_CLOUD_PROJECT"))
parser = GeminiAudioParser()
orchestrator = TaskOrchestrator(TaskRepository(db), parser)

def extract_tasks_from_audio(audio_path: str) -> dict:
    """Extracts action items from an audio file and assigns lanes and classes."""
    correlation_id = str(uuid.uuid4())
    print(f"[TOOL] extract_tasks_from_audio invoked with {audio_path}")
    return orchestrator.process_voice_note(audio_path, correlation_id)

extract_tool = FunctionTool(extract_tasks_from_audio)

class VoiceAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def _run_async_impl(self, ctx):
        node_input = ctx.user_content
        audio_path = ""
        # The prompt is the file path or instruction containing the file path
        if hasattr(node_input, "text"):
            text = node_input.text
        elif hasattr(node_input, "content"):
            text = str(node_input.content)
        elif isinstance(node_input, str):
            text = node_input
        else:
            text = str(node_input)
            
        match = re.search(r'(/[a-zA-Z0-9_\-\./]+)', text)
        if match:
            audio_path = match.group(1)
        else:
            audio_path = text.strip()

        # Run the tool synchronously via to_thread
        result = await asyncio.to_thread(extract_tool.func, audio_path)
        
        # Yield the response back as an Event
        from google.genai import types
        yield Event(message=types.Content(parts=[types.Part.from_text(text=json.dumps(result, indent=2))], role="model"))

agent = VoiceAgent(name="voice_taskmaster")
