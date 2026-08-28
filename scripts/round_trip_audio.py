"""One-shot audio round-trip to verify Vertex + Gemini 3.5 Flash + structured JSON.

Usage:
    uv run python scripts/round_trip_audio.py <path-to-audio>
"""
import sys
from dotenv import dotenv_values
from google import genai
from google.genai import types

cfg = dotenv_values(".env")
audio_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/voice-test/harvard.wav"
mime = "audio/wav" if audio_path.endswith(".wav") else "audio/mp3"

client = genai.Client(
    vertexai=True,
    project=cfg["GOOGLE_CLOUD_PROJECT"],
    location=cfg["GOOGLE_CLOUD_LOCATION"],
)

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

print("--- text ---")
print(resp.text)
print("--- usage ---")
print(resp.usage_metadata)
