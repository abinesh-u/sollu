"""Global registry of task executors.

This acts as a facade over the centralized Task Intent manifest.
"""

from src.domain.intents import INTENTS, get_intent

# Every class the triage schema can emit.
KNOWN_CLASSES = [intent.id for intent in INTENTS]

EXECUTORS = {
    intent.id: intent.executor_instance
    for intent in INTENTS
    if intent.executor_instance is not None
}


def has_executor(task_class: str) -> bool:
    return task_class in EXECUTORS


def get_executor(task_class: str):
    """Returns the executor for a given task class, or None."""
    return EXECUTORS.get(task_class)


def describe(task_class: str) -> dict:
    ex = EXECUTORS.get(task_class)
    intent = get_intent(task_class)
    return {
        "class": task_class,
        "has_executor": ex is not None,
        "executor_kind": getattr(ex, "kind", None),
        "draft_only": bool(getattr(ex, "draft_only", False)),
        "label": getattr(ex, "label", "No executor — approval is recorded only"),
        # UI Metadata from Intent
        "ui_label": intent.ui_label if intent else "Unknown",
        "ui_description": intent.ui_description if intent else "",
        "ui_output_label": intent.ui_output_label if intent else "",
        "ui_icon_name": intent.ui_icon_name if intent else "FileText",
        "reversibility": intent.reversibility.value if intent else "NONE",
    }
