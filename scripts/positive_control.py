"""Positive-control audio round-trip.

Runs the same audio file N times against gemini-3.5-flash with low thinking budget,
logs per-run token breakdown to logs/runs.jsonl, prints the JSON each run.

Usage:
    uv run python scripts/positive_control.py --runs 5 --budget 0
"""
import argparse
import json
import sys
import time
from pathlib import Path

from dotenv import dotenv_values
from google import genai
from google.genai import types


SCHEMA = {
    "type": "object",
    "properties": {
        "tasks": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "task": {"type": "string"},
                    "lane": {"type": "string", "enum": ["now", "next", "later"]},
                },
                "required": ["task", "lane"],
            },
        }
    },
    "required": ["tasks"],
}

PROMPT = (
    "Extract every concrete action item the speaker commits to. "
    "Lane 'now' = blocking today or before tomorrow's standup. "
    "Lane 'next' = a specific this-week commitment with a deadline the speaker named. "
    "Lane 'later' = backlog, watch-only, or 'check if/whether something happens' — no fixed date. "
    "Self-corrections override earlier mentions: if the speaker replaces a task, keep the final one. "
    "Hedged or speculative thoughts ('I'm thinking', 'maybe we should', 'I wonder if', 'probably should') are NOT tasks. "
    "Price watches, drop alerts, and 'check if X happens' requests are lane=later. "
    "If the speaker is not committing to action, return {\"tasks\": []}."
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default="/tmp/voice-test/positive.wav")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--budget", type=int, default=0,
                    help="thinking_budget: 0 disables thinking, None lets model decide")
    ap.add_argument("--model", default="gemini-3.5-flash")
    ap.add_argument("--log", default="logs/runs.jsonl")
    args = ap.parse_args()

    cfg = dotenv_values(".env")
    client = genai.Client(
        vertexai=True,
        project=cfg["GOOGLE_CLOUD_PROJECT"],
        location=cfg["GOOGLE_CLOUD_LOCATION"],
    )

    audio_bytes = Path(args.audio).read_bytes()
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav")

    log_path = Path(args.log)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    thinking = args.budget if args.budget >= 0 else None

    for run_idx in range(1, args.runs + 1):
        t0 = time.perf_counter()
        resp = client.models.generate_content(
            model=args.model,
            contents=[PROMPT, audio_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=SCHEMA,
                temperature=0.0,
                thinking_config=types.ThinkingConfig(
                    thinking_budget=thinking,
                    include_thoughts=False,
                ) if thinking is not None else types.ThinkingConfig(
                    include_thoughts=False,
                ),
            ),
        )
        elapsed = time.perf_counter() - t0

        if resp.text is None:
            raise RuntimeError(f"run {run_idx}: empty response text (finish_reason={resp.candidates[0].finish_reason if resp.candidates else 'unknown'})")
        parsed = json.loads(resp.text)
        u = resp.usage_metadata
        breakdown = {
            "prompt_audio": _modality_tokens(u, "AUDIO"),
            "prompt_text":  _modality_tokens(u, "TEXT"),
            "thoughts":     (u.thoughts_token_count if u and u.thoughts_token_count else 0),
            "candidate":    (u.candidates_token_count if u and u.candidates_token_count else 0),
            "total":        (u.total_token_count if u else 0),
        }

        record = {
            "run": run_idx,
            "model": args.model,
            "thinking_budget": thinking,
            "elapsed_sec": round(elapsed, 3),
            "tokens": breakdown,
            "tasks_count": len(parsed["tasks"]),
            "tasks": parsed["tasks"],
        }
        with log_path.open("a") as f:
            f.write(json.dumps(record) + "\n")

        print(f"\n=== RUN {run_idx}/{args.runs}  ({elapsed:.2f}s) ===")
        print(json.dumps(parsed, indent=2))
        print(f"tokens: {breakdown}")


def _modality_tokens(usage, modality: str) -> int:
    if not usage or not usage.prompt_tokens_details:
        return 0
    for d in usage.prompt_tokens_details:
        if d.modality and d.modality.name == modality:
            return d.token_count or 0
    return 0


if __name__ == "__main__":
    main()
