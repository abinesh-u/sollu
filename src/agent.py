import json
from google import genai
from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from dotenv import dotenv_values

cfg = dotenv_values(".env")

def extract_tasks_from_audio(audio_path: str) -> dict:
    """Extracts action items from an audio file and assigns lanes and classes."""
    print(f"[TOOL] extract_tasks_from_audio invoked with {audio_path}")
    client = genai.Client(
        vertexai=True,
        project=cfg["GOOGLE_CLOUD_PROJECT"],
        location=cfg["GOOGLE_CLOUD_LOCATION"],
    )
    mime = "audio/wav" if audio_path.endswith(".wav") else "audio/mp3"
    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime)
    
    schema = {
        "type": "object",
        "properties": {
            "tasks": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "lane": {"type": "string", "enum": ["now", "next", "later"]},
                        "class": {"type": "string", "enum": ["message_person", "make_call", "research", "watch_price", "other"]},
                    },
                    "required": ["task", "lane", "class"],
                },
            }
        },
        "required": ["tasks"],
    }
    
    resp = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=[
            "Extract every action item the speaker mentions. "
            "Lane 'now' = blocking today, 'next' = this week, 'later' = backlog. "
            "Assign a 'class' to each task from: message_person, make_call, research, watch_price, other. "
            "If the speaker is not giving tasks, return {\"tasks\": []}.",
            audio_part,
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            temperature=0.0,
        ),
    )
    
    # Extract token usage breakdown
    token_usage = {
        "audio": 0,
        "text": 0,
        "candidate": 0,
        "total": 0
    }
    if hasattr(resp, 'usage_metadata') and resp.usage_metadata:
        um = resp.usage_metadata
        token_usage["candidate"] = getattr(um, 'candidates_token_count', 0)
        token_usage["total"] = getattr(um, 'total_token_count', 0)
        
        if hasattr(um, 'prompt_tokens_details') and um.prompt_tokens_details:
            for detail in um.prompt_tokens_details:
                if 'AUDIO' in str(detail.modality):
                    token_usage["audio"] += detail.token_count
                elif 'TEXT' in str(detail.modality):
                    token_usage["text"] += detail.token_count
    
    return {
        "tasks": json.loads(resp.text).get("tasks", []),
        "usage": token_usage
    }

extract_tool = FunctionTool(extract_tasks_from_audio)

from google.adk.agents.base_agent import BaseAgent
from google.adk.events import Event
import asyncio
import json

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
            
        import re
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
