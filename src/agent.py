"""ADK wrapper around the orchestrator — this is the Google Agent Framework
mandatory, and it sits on the live `POST /tasks` path (see main.py).

VoiceAgent is a custom google-adk `BaseAgent`, not an `LlmAgent`: there is
nothing to decide (one voice note in, one triage pass out), so it deterministically
invokes the same `FunctionTool` an `LlmAgent` would call, and yields the result
as an ADK `Event`. `run_voice_agent()` is the only ADK-facing entry point the
rest of the app needs — it owns the Runner/session plumbing so main.py stays a
thin HTTP adapter.
"""
import asyncio
import json

from google.adk.agents.base_agent import BaseAgent
from google.adk.events import Event
from google.adk.runners import InMemoryRunner
from google.adk.tools import FunctionTool
from google.genai import types

from src.singletons import orchestrator


def extract_tasks_from_audio(audio_path: str, correlation_id: str,
                              image_path: str = None, image_mime: str = None,
                              audio_mime: str = None) -> dict:
    """ADK tool: run the orchestrator on one voice note.

    correlation_id is supplied by the caller, never minted here — AGENTS.md's
    logging contract needs the id main.py already generated for the request,
    so one note's whole lifecycle greps out under a single id.
    """
    return orchestrator.process_voice_note(
        audio_path, correlation_id, image_path, image_mime, audio_mime)


extract_tool = FunctionTool(extract_tasks_from_audio)


class VoiceAgent(BaseAgent):
    """Deterministic ADK agent: one voice note in, one triage result out."""

    async def _run_async_impl(self, ctx):
        args = json.loads(ctx.user_content.parts[0].text)
        result = await asyncio.to_thread(extract_tool.func, **args)
        yield Event(
            author=self.name,
            content=types.Content(
                parts=[types.Part.from_text(text=json.dumps(result))],
                role="model"))


agent = VoiceAgent(name="voice_taskmaster")
_runner = InMemoryRunner(agent=agent, app_name="voice_taskmaster")


async def run_voice_agent(audio_path: str, correlation_id: str,
                           image_path: str = None, image_mime: str = None,
                           audio_mime: str = None) -> dict:
    """main.py's entry point: drive the ADK Runner for one voice note.

    Creates a throwaway session keyed to correlation_id, sends the tool's
    arguments as one JSON user message, and unpacks the JSON payload the
    agent yields back.
    """
    session = await _runner.session_service.create_session(
        app_name="voice_taskmaster", user_id="voice_agent",
        session_id=correlation_id)
    message = types.Content(
        parts=[types.Part.from_text(text=json.dumps({
            "audio_path": audio_path,
            "correlation_id": correlation_id,
            "image_path": image_path,
            "image_mime": image_mime,
            "audio_mime": audio_mime,
        }))],
        role="user")

    result = None
    async for event in _runner.run_async(
            user_id="voice_agent", session_id=session.id, new_message=message):
        if event.content and event.content.parts and event.content.parts[0].text:
            result = json.loads(event.content.parts[0].text)
    return result
