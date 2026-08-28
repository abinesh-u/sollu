"""Runs the executor for an approved task and writes the artifact onto its doc.

Both approval paths funnel through here:
  - manual approval  -> inline, from /api/tasks/{id}/approve
  - auto-approval    -> background, queued by POST /tasks

An executor failure is recorded on the task and never propagates: a failed
research call must not fail the upload that produced five perfectly good tasks.
"""
import concurrent.futures

from google.cloud import firestore

from src.domain.logger import log_event
from src.executors.base import (
    FAILED,
    MAX_ATTEMPTS,
    MAX_TOOL_CALLS,
    NO_EXECUTOR,
    ExecutionResult,
    ExecutorTimeout,
)
from src.executors.registry import get_executor

# Deadlines are enforced here, not by the SDK: HttpOptions.timeout is an httpx
# read timeout, so a grounded call that keeps its connection alive can run for
# minutes under a 45s setting. A blown deadline leaves its worker thread to
# finish and be discarded — the task is already recorded as failed by then.
_pool = concurrent.futures.ThreadPoolExecutor(max_workers=4,
                                              thread_name_prefix="executor")


def _run_with_deadline(executor, task_data: dict) -> ExecutionResult:
    deadline = getattr(executor, "deadline_seconds", 45)
    future = _pool.submit(executor.run, task_data)
    try:
        return future.result(timeout=deadline)
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise ExecutorTimeout(f"exceeded {deadline}s deadline") from None


def run_for_task(db: firestore.Client, task_id: str, task_data: dict,
                 correlation_id: str) -> dict:
    task_class = task_data.get("class", "other")
    executor = get_executor(task_class)
    doc_ref = db.collection("tasks").document(task_id)

    if executor is None:
        update = {"execution_status": NO_EXECUTOR, "artifact": None}
        doc_ref.update(update)
        log_event(correlation_id, "execution complete",
                  task_id=task_id, task_class=task_class, execution_status=NO_EXECUTOR)
        return update

    result = None
    error = None
    tool_calls_used = 0
    attempt = 0

    # One retry on a transient failure, inside a hard cap on model invocations.
    # Today's executors each make a single call, so with one retry this budget
    # is not reachable — it bounds a future multi-call executor. The cap that
    # *does* bite in practice is on searches, checked after the call below:
    # Gemini's built-in Search runs server-side and cannot be limited from here,
    # so it is observed and logged rather than enforced.
    while attempt < MAX_ATTEMPTS:
        attempt += 1
        if tool_calls_used + 1 > MAX_TOOL_CALLS:
            log_event(correlation_id, "tool cap hit",
                      task_id=task_id, task_class=task_class, kind="model_calls",
                      cap=MAX_TOOL_CALLS, used=tool_calls_used, enforced=True)
            break
        try:
            result = _run_with_deadline(executor, task_data)
            tool_calls_used += result.tool_calls
            error = None
            break
        except ExecutorTimeout as e:
            # Never retry a timeout — that just doubles the wait before the card
            # shows anything.
            error = f"Timed out: {e}"
            tool_calls_used += 1
            log_event(correlation_id, "execution timed out",
                      task_id=task_id, task_class=task_class, attempt=attempt)
            break
        except Exception as e:
            error = f"{type(e).__name__}: {e}"
            tool_calls_used += 1
            log_event(correlation_id, "execution attempt failed",
                      task_id=task_id, task_class=task_class,
                      attempt=attempt, error=error[:300])

    if result is None:
        result = ExecutionResult(artifact="", status=FAILED, error=error)

    if len(result.search_queries) > MAX_TOOL_CALLS:
        log_event(correlation_id, "tool cap hit",
                  task_id=task_id, task_class=task_class, kind="google_search",
                  cap=MAX_TOOL_CALLS, used=len(result.search_queries),
                  enforced=False,
                  note="built-in Search runs server-side; observed, not capped")

    update = {
        "execution_status": result.status,
        "artifact": result.artifact or None,
        "grounded": result.grounded,
        "sources": result.sources,
        "execution_usage": result.usage,
        "execution_seconds": result.elapsed_seconds,
        "execution_error": result.error,
        "executed_at": firestore.SERVER_TIMESTAMP,
    }
    doc_ref.update(update)

    log_event(correlation_id, "execution complete",
              task_id=task_id,
              task_class=task_class,
              execution_status=result.status,
              grounded=result.grounded,
              search_queries=result.search_queries,
              elapsed_seconds=result.elapsed_seconds,
              tool_calls=tool_calls_used,
              error=result.error)

    update["executed_at"] = None  # SERVER_TIMESTAMP sentinel is not JSON-serialisable
    return update


def run_auto_approved(db: firestore.Client, queued: list[dict]) -> None:
    """Background entrypoint. `queued` carries each task's own correlation_id so
    the log shows one lifecycle from note received through execution complete."""
    for item in queued:
        try:
            run_for_task(db, item["id"], item["data"], item["correlation_id"])
        except Exception as e:
            # Belt and braces: the background task must never raise.
            log_event(item.get("correlation_id", "unknown"), "execution crashed",
                      task_id=item.get("id"), error=f"{type(e).__name__}: {e}"[:300])
