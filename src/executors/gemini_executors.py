"""gemini-3.5-flash executors: research, message_person, make_call.

All three share one client. `research` is the only one with a tool attached.

Latency note (measured against Vertex `global` during planning): the same
grounded prompt ran 18.7s with a response_schema and 244s without one. The
schema is therefore not optional here — it is what keeps the call inside the
timeout. Thinking is left at its default: AGENTS.md locks thinking_budget=0 for
*triage*, and with tools attached a zero budget stalls rather than erroring.
"""
import json
import time

from google.genai import types

from src.domain.vertex import vertex_client
from src.executors.base import (
    DRAFT_READY,
    EXECUTED,
    MAX_TOOL_CALLS,
    ExecutionResult,
)

# One client for all three executors. Per-executor HttpOptions.timeout values
# bought nothing — that setting is an httpx read timeout, not a wall-clock
# deadline (a grounded call ran 244s under a 40s setting), so the real deadline
# lives in executor_runner. Two clients only meant paying the first-call
# connection cost twice on a cold instance.
_client = None


def _gemini() -> "object":
    global _client
    if _client is None:
        _client = vertex_client()
    return _client


def warm_up() -> None:
    """Build the client ahead of the first real task.

    Called at app startup so a cold instance pays connection setup before a
    user is waiting on it, rather than inside a deadline-bounded executor.
    """
    _gemini()


def _usage(resp) -> dict:
    um = getattr(resp, "usage_metadata", None)
    if not um:
        return {}
    return {
        "prompt": getattr(um, "prompt_token_count", 0) or 0,
        "candidate": getattr(um, "candidates_token_count", 0) or 0,
        "total": getattr(um, "total_token_count", 0) or 0,
    }


RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "finding": {"type": "string", "description": "Two or three sentences answering the task."},
        "sources": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["finding"],
}


class ResearchExecutor:
    kind = "gemini_search"
    draft_only = False
    deadline_seconds = 45
    label = "Gemini 3.5 Flash with Google Search grounding"

    def run(self, task: dict) -> ExecutionResult:
        t0 = time.perf_counter()
        resp = _gemini().models.generate_content(
            model="gemini-3.5-flash",
            contents=(
                "Research this task and answer it directly in two or three sentences. "
                "Use web search. Prefer specific figures and dates over generalities. "
                f"Task: {task.get('task', '')}"
            ),
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
                response_mime_type="application/json",
                response_schema=RESEARCH_SCHEMA,
                temperature=0.0,
            ),
        )
        elapsed = time.perf_counter() - t0

        # Grounding is read off the metadata, never inferred from the prose.
        queries: list[str] = []
        chunks = 0
        if resp.candidates:
            gm = resp.candidates[0].grounding_metadata
            if gm:
                queries = list(gm.web_search_queries or [])
                chunks = len(gm.grounding_chunks or [])

        parsed = json.loads(resp.text)
        finding = parsed.get("finding", "").strip()
        sources = parsed.get("sources") or []
        if sources:
            finding = f"{finding}\n\nSources: " + ", ".join(sources[:3])

        return ExecutionResult(
            artifact=finding,
            status=EXECUTED,
            grounded=bool(queries or chunks),
            tool_calls=1,
            usage=_usage(resp),
            elapsed_seconds=round(elapsed, 2),
            search_queries=queries,
        )


class _DraftExecutor:
    """Produces text a human still has to send. Nothing leaves the system."""
    draft_only = True
    deadline_seconds = 30
    prompt = ""

    def run(self, task: dict) -> ExecutionResult:
        t0 = time.perf_counter()
        resp = _gemini().models.generate_content(
            model="gemini-3.5-flash",
            contents=f"{self.prompt}\nTask: {task.get('task', '')}",
            config=types.GenerateContentConfig(
                temperature=0.2,
                # No tools attached, so a zero thinking budget is safe here and
                # keeps the draft fast.
                thinking_config=types.ThinkingConfig(
                    thinking_budget=0, include_thoughts=False
                ),
            ),
        )
        return ExecutionResult(
            artifact=(resp.text or "").strip(),
            status=DRAFT_READY,
            tool_calls=1,
            usage=_usage(resp),
            elapsed_seconds=round(time.perf_counter() - t0, 2),
        )


class MessagePersonExecutor(_DraftExecutor):
    kind = "gemini_draft"
    label = "Gemini 3.5 Flash draft message (not sent)"
    prompt = (
        "Draft a short, friendly message the speaker could send to carry out this "
        "task. Three sentences at most. Output only the message body — no subject "
        "line, no preamble, no commentary."
    )


class MakeCallExecutor(_DraftExecutor):
    kind = "gemini_draft"
    label = "Gemini 3.5 Flash call script (no call placed)"
    prompt = (
        "Write a short call script for the speaker to follow when making this call: "
        "an opening line, the two or three points to cover, and what to confirm "
        "before hanging up. Output only the script."
    )


__all__ = [
    "ResearchExecutor",
    "MessagePersonExecutor",
    "MakeCallExecutor",
    "MAX_TOOL_CALLS",
]
