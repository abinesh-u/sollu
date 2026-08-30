"""Centralized manifest for all Task Intents in the voice agent."""
import os
from enum import Enum
from dataclasses import dataclass
from typing import Any, Optional

from src.executors.gemini_executors import ResearchExecutor
from src.executors.price_executor import WatchPriceExecutor
from src.executors.mcp_executor import McpExecutor

class Reversibility(Enum):
    HARD = "HARD"  # Irreversible, externally visible (e.g. sending email)
    SOFT = "SOFT"  # 2-second undo, internal state only (e.g. creating a task, logging expense)
    NONE = "NONE"  # Read-only or safe background task

@dataclass
class TaskIntent:
    id: str
    prompt_instruction: str
    ui_label: str
    ui_description: str
    ui_output_label: str
    ui_icon_name: str
    reversibility: Reversibility
    executor_instance: Optional[Any] = None

# Get MCP URLs from env, with a safe fallback to the internal FastAPI app (Option 2)
mcp_url = os.getenv("INTERNAL_MCP_URL", f"http://localhost:{os.environ.get('PORT', 8080)}/sse")

INTENTS = [
    TaskIntent(
        id="send_email",
        prompt_instruction="send_email",
        ui_label="Send Email",
        ui_description="Email sent via Gmail API.",
        ui_output_label="Sent Receipt",
        ui_icon_name="Mail",
        reversibility=Reversibility.HARD,
        executor_instance=McpExecutor(label="MCP (Gmail)", mcp_server_url=mcp_url)
    ),
    TaskIntent(
        id="add_todo_task",
        prompt_instruction="add_todo_task",
        ui_label="Add Task",
        ui_description="Task added via Google Tasks.",
        ui_output_label="Task ID",
        ui_icon_name="CheckSquare",
        reversibility=Reversibility.SOFT,
        executor_instance=McpExecutor(label="MCP (Tasks)", mcp_server_url=mcp_url)
    ),
    TaskIntent(
        id="append_to_doc",
        prompt_instruction="append_to_doc",
        ui_label="Brain Dump",
        ui_description="Appended via Google Docs.",
        ui_output_label="Revision ID",
        ui_icon_name="FileText",
        reversibility=Reversibility.SOFT,
        executor_instance=McpExecutor(label="MCP (Docs)", mcp_server_url=mcp_url)
    ),
    TaskIntent(
        id="log_expense",
        prompt_instruction="log_expense",
        ui_label="Log Expense",
        ui_description="Logged via Google Sheets.",
        ui_output_label="Row added",
        ui_icon_name="DollarSign",
        reversibility=Reversibility.SOFT,
        executor_instance=McpExecutor(label="MCP (Sheets)", mcp_server_url=mcp_url)
    ),
    TaskIntent(
        id="create_calendar_event",
        prompt_instruction="create_calendar_event",
        ui_label="Schedule Event",
        ui_description="Scheduled via Google Calendar.",
        ui_output_label="Event Link",
        ui_icon_name="Calendar",
        reversibility=Reversibility.SOFT,
        executor_instance=McpExecutor(label="MCP (Calendar)", mcp_server_url=mcp_url)
    ),
    TaskIntent(
        id="research",
        prompt_instruction="research",
        ui_label="Grounded Research",
        ui_description="Web search executed and summarized.",
        ui_output_label="Research synthesis",
        ui_icon_name="Search",
        reversibility=Reversibility.NONE,
        executor_instance=ResearchExecutor()
    ),
    TaskIntent(
        id="watch_price",
        prompt_instruction="watch_price",
        ui_label="Watch Condition",
        ui_description="Condition registered for deferred evaluation.",
        ui_output_label="Condition recorded",
        ui_icon_name="TrendingUp",
        reversibility=Reversibility.NONE,
        executor_instance=WatchPriceExecutor()
    ),
    TaskIntent(
        id="other",
        prompt_instruction="other",
        ui_label="General Task",
        ui_description="No executor — approval is recorded only.",
        ui_output_label="Execution result",
        ui_icon_name="FileText",
        reversibility=Reversibility.NONE,
        executor_instance=None
    )
]

def get_intent(intent_id: str) -> Optional[TaskIntent]:
    for i in INTENTS:
        if i.id == intent_id:
            return i
    return None
