import unittest
from unittest.mock import MagicMock, patch
from src.domain.executor_runner import run_for_task, run_auto_approved
from src.executors.base import NO_EXECUTOR, ExecutionResult, DRAFT_READY, ExecutorTimeout, FAILED
from tests.test_trust_ladder import FakeFirestoreClient


class TestExecutorRunner(unittest.TestCase):
    def setUp(self):
        self.db = FakeFirestoreClient()

    def test_unregistered_class_sets_no_executor_status(self):
        """Slice 1: An unknown task class must record NO_EXECUTOR status and artifact=None."""
        self.db.collection("tasks").document("task-1").set({
            "class": "unknown_future_class", "task": "Do something"
        })

        result = run_for_task(
            db=self.db,
            task_id="task-1",
            task_data={"class": "unknown_future_class", "task": "Do something"},
            correlation_id="test-cid-1"
        )

        self.assertEqual(result["execution_status"], NO_EXECUTOR)
        self.assertIsNone(result["artifact"])
        task_doc = self.db.collection("tasks").document("task-1").get().to_dict()
        self.assertEqual(task_doc["execution_status"], NO_EXECUTOR)
        self.assertIsNone(task_doc["artifact"])

    def test_successful_execution_persists_artifact_and_metadata(self):
        """Slice 2: A successful executor run must persist artifact, sources, grounded, and usage."""
        self.db.collection("tasks").document("task-2").set({
            "class": "message_person", "task": "Send message to Alice"
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
                db=self.db,
                task_id="task-2",
                task_data={"class": "message_person", "task": "Send message to Alice"},
                correlation_id="test-cid-2"
            )

        mock_executor.run.assert_called_once()
        self.assertEqual(result["execution_status"], DRAFT_READY)
        self.assertEqual(result["artifact"], "Hey Alice, let's sync tomorrow.")
        task_doc = self.db.collection("tasks").document("task-2").get().to_dict()
        self.assertEqual(task_doc["artifact"], "Hey Alice, let's sync tomorrow.")
        self.assertEqual(task_doc["execution_status"], DRAFT_READY)
        self.assertFalse(task_doc["grounded"])
        self.assertEqual(task_doc["execution_seconds"], 1.25)

    def test_executor_timeout_fails_without_retry(self):
        """Slice 3: ExecutorTimeout must record status='failed', error message, and NOT retry."""
        self.db.collection("tasks").document("task-3").set({
            "class": "research", "task": "Investigate database options"
        })

        mock_executor = MagicMock()
        mock_executor.run.side_effect = ExecutorTimeout("exceeded 45s deadline")
        mock_executor.deadline_seconds = 45

        with patch("src.domain.executor_runner.get_executor", return_value=mock_executor):
            result = run_for_task(
                db=self.db,
                task_id="task-3",
                task_data={"class": "research", "task": "Investigate database options"},
                correlation_id="test-cid-3"
            )

        mock_executor.run.assert_called_once()
        self.assertEqual(result["execution_status"], FAILED)
        self.assertIn("Timed out", result["execution_error"])
        task_doc = self.db.collection("tasks").document("task-3").get().to_dict()
        self.assertEqual(task_doc["execution_status"], FAILED)
        self.assertIn("Timed out", task_doc["execution_error"])
        self.assertIsNone(task_doc["artifact"])

    def test_run_auto_approved_processes_all_items_with_error_containment(self):
        """Slice 4: run_auto_approved must process all items and contain crashes."""
        self.db.collection("tasks").document("t-1").set({"class": "unknown_1", "task": "Task 1"})
        self.db.collection("tasks").document("t-2").set({"class": "unknown_2", "task": "Task 2"})

        queued = [
            {"id": "t-1", "data": {"class": "unknown_1", "task": "Task 1"}, "correlation_id": "cid-1"},
            {"id": "t-2", "data": {"class": "unknown_2", "task": "Task 2"}, "correlation_id": "cid-2"},
        ]

        run_auto_approved(self.db, queued)

        task_1 = self.db.collection("tasks").document("t-1").get().to_dict()
        task_2 = self.db.collection("tasks").document("t-2").get().to_dict()
        self.assertEqual(task_1["execution_status"], NO_EXECUTOR)
        self.assertEqual(task_2["execution_status"], NO_EXECUTOR)


if __name__ == "__main__":
    unittest.main()
