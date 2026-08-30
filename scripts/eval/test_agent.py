"""Smoke test for the ADK-wired path: run one voice note through src.agent
exactly as main.py's POST /tasks handler does.

Usage:
    uv run python scripts/test_agent.py [audio_path] [correlation_id]
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from src.agent import run_voice_agent


def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else "/tmp/voice-test/positive.wav"
    correlation_id = sys.argv[2] if len(sys.argv) > 2 else "test-agent-script"

    print(f"Running the ADK agent for: {audio_path} (correlation_id={correlation_id})")
    result = asyncio.run(run_voice_agent(audio_path, correlation_id))

    print("\n--- Agent Response ---")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
