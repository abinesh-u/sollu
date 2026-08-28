"""One mapping from task class to executor.

All class-specific execution behaviour goes through this dict. Nothing else in
the codebase should branch on task class.
"""
from src.executors.gemini_executors import (
    MakeCallExecutor,
    MessagePersonExecutor,
    ResearchExecutor,
)
from src.executors.price_executor import WatchPriceExecutor

# Every class the triage schema can emit (src/domain/parser.py). `other` is
# present with no executor so the UI can say so explicitly.
KNOWN_CLASSES = ["message_person", "make_call", "research", "watch_price", "other"]

EXECUTORS = {
    "research": ResearchExecutor(),
    "message_person": MessagePersonExecutor(),
    "make_call": MakeCallExecutor(),
    "watch_price": WatchPriceExecutor(),
}


def has_executor(task_class: str) -> bool:
    return task_class in EXECUTORS


def get_executor(task_class: str):
    return EXECUTORS.get(task_class)


def describe(task_class: str) -> dict:
    ex = EXECUTORS.get(task_class)
    return {
        "class": task_class,
        "has_executor": ex is not None,
        "executor_kind": getattr(ex, "kind", None),
        "draft_only": bool(getattr(ex, "draft_only", False)),
        "label": getattr(ex, "label", "No executor — approval is recorded only"),
    }
