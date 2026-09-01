"""One-shot audio round-trip to verify Vertex + Gemini 3.5 Flash + structured JSON.

Usage:
    uv run python scripts/round_trip_audio.py <path-to-audio>
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import json

from src.domain.parser import GeminiAudioParser

audio_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/voice-test/harvard.wav"
mime = "audio/wav" if audio_path.endswith(".wav") else "audio/mp3"

with open(audio_path, "rb") as f:
    audio_bytes = f.read()

parser = GeminiAudioParser()
tasks, usage = parser.parse_audio(audio_bytes, mime)

print("--- tasks ---")
print(json.dumps(tasks, indent=2))
print("--- usage ---")
print(json.dumps(usage, indent=2))
