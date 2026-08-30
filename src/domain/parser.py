import json
from google import genai
from google.genai import types

from src.domain.vertex import vertex_client
from src.domain.intents import INTENTS, TaskIntent

def build_extraction_config(intents: list[TaskIntent]) -> tuple[str, dict]:
    """Builds the prompt and JSON schema for task extraction.
    
    This acts as a true seam, allowing us to unit test the LLM instructions
    and schema configuration without hitting the Vertex API.
    """
    intent_prompt_list = ", ".join([i.prompt_instruction for i in intents])
    
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
                        "class": {"type": "string", "enum": [i.id for i in intents]},
                        "condition": {"type": "string", "description": "The specific condition to monitor for 'later' lane tasks (e.g., 'price drops below 15000')"},
                        "defer_duration_minutes": {"type": "integer", "description": "How many minutes to defer checking this condition"},
                        "source": {"type": "string", "enum": ["audio", "image", "both"], "description": "Where this task came from. 'audio' when the speaker stated it and the image added nothing."},
                        "evidence": {"type": "string", "description": "If the image was used, what it showed. Null if audio-only."},
                        "unresolved_recipient": {"type": "boolean", "description": "True if the task involves emailing/messaging a person (e.g. 'Email Priya') but their exact email address was not spoken. False if no person is involved, or if the exact email is known."}
                    },
                    "required": ["task", "lane", "class", "source"],
                },
            }
        },
        "required": ["tasks"],
    }
    
    prompt = (
        "You are an assistant that extracts concrete tasks from a speaker's voice note. "
        "Tasks are things the speaker commits to doing, or asks you to do. "
        "Extract every concrete action item the speaker commits to. "
        "Lane 'now' = blocking today or before tomorrow's standup. "
        "Lane 'next' = a specific this-week commitment with a deadline the speaker named. "
        "Lane 'later' = backlog, watch-only, or 'check if/whether something happens' — no fixed date. "
        "Self-corrections override earlier mentions: if the speaker replaces a task, keep the final one. "
        "Hedged or speculative thoughts ('I'm thinking', 'maybe we should', 'I wonder if', 'probably should') are NOT tasks. "
        "Price watches, drop alerts, and 'check if X happens' requests are lane=later. "
        f"Assign a 'class' to each task from: {intent_prompt_list}. "
        "For lane='later' tasks, set 'condition' to the specific thing to watch for. "
        "If the speaker is not committing to action, return {\"tasks\": []}. "
        "An image may be attached alongside the audio. It is supporting evidence "
        "for what the speaker said, NOT a second source of tasks — do not invent "
        "tasks that the speaker did not commit to. When the image contains a "
        "detail that bears on a task, set 'source' to 'both' and set 'evidence' "
        "to the detail that would actually change the decision — prefer the "
        "concrete number, price, date or deadline you read over a general label "
        "or a route. Quote it as it appears. "
        "Otherwise set 'source' to 'audio' and leave 'evidence' empty."
    )
    
    return prompt, schema


class GeminiAudioParser:
    def __init__(self, project: str = None, location: str = "global"):
        if project:
            self.client = genai.Client(
                vertexai=True,
                project=project,
                location=location,
            )
        else:
            # Same builder the executors use — one config path, no drift.
            self.client = vertex_client()

        # Cache the config so we don't rebuild it on every request
        self.prompt, self.schema = build_extraction_config(INTENTS)

    def parse_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav",
                    image_bytes: bytes = None, image_mime: str = None) -> tuple[list, dict]:
        """Parses audio bytes into structured tasks and returns token usage.

        An optional image rides in the SAME request as a second content part —
        one call, one triage decision. The image is supporting evidence for what
        the speaker said, not a second source of tasks.
        """
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)

        parts = [audio_part]
        if image_bytes:
            parts.append(types.Part.from_bytes(
                data=image_bytes, mime_type=image_mime or "image/jpeg"))

        resp = self.client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[self.prompt, *parts],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=self.schema,
                temperature=0.0,
                # Locked in AGENTS.md: thinking budget 0 for triage. Without this the
                # model thinks on every call — ~4x latency and ~2.5x tokens per note.
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0,
                    include_thoughts=False,
                ),
            ),
        )
        
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
        
        tasks_list = json.loads(resp.text).get("tasks", [])
        return tasks_list, token_usage

    def parse_text(self, text: str, image_bytes: bytes = None, image_mime: str = None) -> tuple[list, dict]:
        """Parses a text transcript into structured tasks and returns token usage."""
        parts = [text]
        if image_bytes:
            parts.append(types.Part.from_bytes(
                data=image_bytes, mime_type=image_mime or "image/jpeg"))

        resp = self.client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[self.prompt, *parts],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=self.schema,
                temperature=0.0,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0,
                    include_thoughts=False,
                ),
            ),
        )
        
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
                    if 'TEXT' in str(detail.modality):
                        token_usage["text"] += detail.token_count
        
        tasks_list = json.loads(resp.text).get("tasks", [])
        return tasks_list, token_usage
