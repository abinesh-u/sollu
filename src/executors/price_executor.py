"""watch_price executor.

Delegates to the existing ConditionEvaluator rather than reimplementing it, so
there is one stubbed price/weather source in the codebase, not two.
"""

import time

from src.domain.evaluator import ConditionEvaluator
from src.executors.base import EXECUTED, ExecutionResult

_evaluator = ConditionEvaluator()


class WatchPriceExecutor:
    kind = "condition_evaluator"
    draft_only = False
    deadline_seconds = 10
    label = "Deferred condition evaluator (stubbed price source)"

    def run(self, task: dict) -> ExecutionResult:
        t0 = time.perf_counter()
        condition = task.get("condition") or ""
        met = _evaluator.evaluate(condition)
        artifact = (
            f"Condition met: {condition}"
            if met
            else f"Not yet — still watching: {condition or 'no condition recorded'}"
        )
        return ExecutionResult(
            artifact=artifact,
            status=EXECUTED,
            tool_calls=1,
            elapsed_seconds=round(time.perf_counter() - t0, 2),
        )
