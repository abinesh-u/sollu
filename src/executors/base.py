"""Shared types for executors.

An executor turns an approved task into an artifact. It never sends, posts, or
places anything externally — `message_person` and `make_call` produce drafts
that a human still has to act on.
"""

from dataclasses import dataclass, field

# execution_status values written onto the task document.
EXECUTING = "executing"
EXECUTED = "executed"
DRAFT_READY = "draft_ready"
NO_EXECUTOR = "no_executor"
FAILED = "failed"

# task lifecycle status — assigned by the trust ladder, read by approval transitions
AUTO_APPROVED = "auto_approved"
PENDING_APPROVAL = "pending_approval"
APPROVED = "approved"
REJECTED = "rejected"

# Hard cap on model invocations inside a single task execution.
MAX_TOOL_CALLS = 3
# Initial call plus one retry.
MAX_ATTEMPTS = 2


class ExecutorTimeout(Exception):
    """Raised when an executor blows its wall-clock deadline.

    google-genai's HttpOptions.timeout is an httpx read timeout — time between
    bytes — not a total-elapsed deadline. A grounded call that keeps the
    connection alive sails straight past it (measured: 244s under a 40s
    setting), so the runner enforces the real deadline itself.
    """


@dataclass
class ExecutionResult:
    artifact: str
    status: str
    grounded: bool = False
    tool_calls: int = 0
    usage: dict = field(default_factory=dict)
    elapsed_seconds: float = 0.0
    search_queries: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    receipt: dict = field(default_factory=dict)
    error: str | None = None
