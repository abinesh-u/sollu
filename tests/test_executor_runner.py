import unittest
from unittest.mock import MagicMock
from src.domain.executor_runner import run_for_task
from src.executors.base import NO_EXECUTOR


class FakeTaskRepository:
    """In-memory task repository adapter for seam testing."""
    def __init__(self, initial_tasks=None):
        self.tasks = initial_tasks or {}
        self.updates = []

    def update(self, task_id: str, fields: dict):
        if task_id not in self.tasks:
            self.tasks[task_id] = {}
        self.tasks[task_id].update(fields)
        self.updates.append((task_id, fields))

    def get_or_raise(self, task_id: str) -> dict:
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        data = dict(self.tasks[task_id])
        data["id"] = task_id
        return data


class TestExecutorRunner(unittest.TestCase):
    def test_unregistered_class_sets_no_executor_status(self):
        """Slice 1: An unknown task class must record NO_EXECUTOR status and artifact=None."""
        repo = FakeTaskRepository({
            "task-1": {"class": "unknown_future_class", "task": "Do something"}
        })

        result = run_for_task(
            repo=repo,
            task_id="task-1",
            task_data={"class": "unknown_future_class", "task": "Do something"},
            correlation_id="test-cid-1"
        )

        self.assertEqual(result["execution_status"], NO_EXECUTOR)
        self.assertIsNone(result["artifact"])
        self.assertEqual(repo.tasks["task-1"]["execution_status"], NO_EXECUTOR)
        self.assertIsNone(repo.tasks["task-1"]["artifact"])

    def test_successful_execution_persists_artifact_and_metadata(self):
        """Slice 2: A successful executor run must persist artifact, sources, grounded, and usage."""
        from unittest.mock import patch
        from src.executors.base import ExecutionResult, DRAFT_READY

        repo = FakeTaskRepository({
            "task-2": {"class": "message_person", "task": "Send message to Alice"}
        })

        mock_result = ExecutionResult(
            artifact="Hey Alice, let's sync tomorrow.",
            status=DRAFT_READY,
            grounded=False,
            sources=[],
            usage={"candidate": 12, "total": 45},
            elapsed_seconds=1.25,
            tool_calls=1
        )

        mock_executor = MagicMock()
        mock_executor.run.return_value = mock_result
        mock_executor.deadline_seconds = 10

        with patch("src.domain.executor_runner.get_executor", return_value=mock_executor):
            result = run_for_task(
                repo=repo,
                task_id="task-2",
                task_data={"class": "message_person", "task": "Send message to Alice"},
                correlation_id="test-cid-2"
            )

        mock_executor.run.assert_called_once()
        self.assertEqual(result["execution_status"], DRAFT_READY)
        self.assertEqual(result["artifact"], "Hey Alice, let's sync tomorrow.")
        self.assertEqual(repo.tasks["task-2"]["artifact"], "Hey Alice, let's sync tomorrow.")
        self.assertEqual(repo.tasks["task-2"]["execution_status"], DRAFT_READY)
        self.assertFalse(repo.tasks["task-2"]["grounded"])
        self.assertEqual(repo.tasks["task-2"]["execution_seconds"], 1.25)

    def test_executor_timeout_fails_without_retry(self):
        """Slice 3: ExecutorTimeout must record status='failed', error message, and NOT retry."""
        from unittest.mock import patch
        from src.executors.base import ExecutorTimeout, FAILED

        repo = FakeTaskRepository({
            "task-3": {"class": "research", "task": "Investigate database options"}
        })

        mock_executor = MagicMock()
        mock_executor.run.side_effect = ExecutorTimeout("exceeded 45s deadline")
        mock_executor.deadline_seconds = 45

        with patch("src.domain.executor_runner.get_executor", return_value=mock_executor):
            result = run_for_task(
                repo=repo,
                task_id="task-3",
                task_data={"class": "research", "task": "Investigate database options"},
                correlation_id="test-cid-3"
            )

        # Must only call run once (no retry on timeout)
        self.assertEqual(mock_executor.run.call_count, 1)
        self.assertEqual(result["execution_status"], FAILED)
        self.assertIn("Timed out", result["execution_error"])
        self.assertEqual(repo.tasks["task-3"]["execution_status"], FAILED)
        self.assertIn("Timed out", repo.tasks["task-3"]["execution_error"])
        self.assertIsNone(repo.tasks["task-3"]["artifact"])

    def test_run_auto_approved_processes_all_items_with_error_containment(self):
        """Slice 4: run_auto_approved must process all items and contain crashes."""
        from unittest.mock import patch
        from src.domain.executor_runner import run_auto_approved

        repo = FakeTaskRepository({
            "t-1": {"class": "unknown_1", "task": "Task 1"},
            "t-2": {"class": "unknown_2", "task": "Task 2"},
        })

        queued = [
            {"id": "t-1", "data": repo.tasks["t-1"], "correlation_id": "cid-1"},
            {"id": "t-2", "data": repo.tasks["t-2"], "correlation_id": "cid-2"},
        ]

        # run_auto_approved must complete without raising
        run_auto_approved(repo, queued)

        self.assertEqual(repo.tasks["t-1"]["execution_status"], NO_EXECUTOR)
        self.assertEqual(repo.tasks["t-2"]["execution_status"], NO_EXECUTOR)


if __name__ == "__main__":
    unittest.main()
