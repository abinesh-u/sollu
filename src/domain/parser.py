import json
from google import genai
from google.genai import types

from src.domain.vertex import vertex_client

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

        self.schema = {
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
                            "condition": {"type": "string", "description": "The specific condition to monitor for 'later' lane tasks (e.g., 'price drops below 15000')"},
                            "defer_duration_minutes": {"type": "integer", "description": "How many minutes to defer checking this condition"}
                        },
                        "required": ["task", "lane", "class"],
                    },
                }
            },
            "required": ["tasks"],
        }

    def parse_audio(self, audio_bytes: bytes, mime_type: str = "audio/wav") -> tuple[list, dict]:
        """Parses audio bytes into structured tasks and returns token usage."""
        audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
        
        resp = self.client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[
                # Rules below are the prompt verified 5/5 by scripts/positive_control.py.
                # The hedge-exclusion and self-correction lines are load-bearing: without
                # them the model extracts speculative asides as tasks.
                "Extract every concrete action item the speaker commits to. "
                "Lane 'now' = blocking today or before tomorrow's standup. "
                "Lane 'next' = a specific this-week commitment with a deadline the speaker named. "
                "Lane 'later' = backlog, watch-only, or 'check if/whether something happens' — no fixed date. "
                "Self-corrections override earlier mentions: if the speaker replaces a task, keep the final one. "
                "Hedged or speculative thoughts ('I'm thinking', 'maybe we should', 'I wonder if', 'probably should') are NOT tasks. "
                "Price watches, drop alerts, and 'check if X happens' requests are lane=later. "
                "Assign a 'class' to each task from: message_person, make_call, research, watch_price, other. "
                "For lane='later' tasks, set 'condition' to the specific thing to watch for. "
                "If the speaker is not committing to action, return {\"tasks\": []}.",
                audio_part,
            ],
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
