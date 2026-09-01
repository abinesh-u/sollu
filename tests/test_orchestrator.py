import unittest
from unittest.mock import MagicMock, patch

from src.domain.orchestrator import TaskOrchestrator, normalise_audio_mime


class FakeTaskRepository:
    """In-memory task repository adapter for seam testing."""

    def __init__(self, initial_tasks=None):
        self.tasks = initial_tasks or {}
        self.updates = []
        self._db = None

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

    def list_deferred_ready(self, now_epoch: int = None):
        return []


class FakeTrustEngine:
    def __init__(self, default_status="pending_approval"):
        self.default_status = default_status
        self.approvals_recorded = []
        self.demotions_recorded = []

    def get_status_for_task(self, task: dict, correlation_id: str) -> str:
        return self.default_status

    def record_approval(self, task_class: str, correlation_id: str):
        self.approvals_recorded.append((task_class, correlation_id))

    def record_demotion(self, task_class: str, correlation_id: str):
        self.demotions_recorded.append((task_class, correlation_id))


class FakeParser:
    def __init__(self, tasks=None, usage=None):
        self.tasks = tasks or []
        self.usage = usage or {"audio": 100, "text": 50, "candidate": 20, "total": 170}

    def parse_audio(self, audio_bytes, mime, image_bytes=None, image_mime=None):
        return self.tasks, self.usage


class TestTaskOrchestrator(unittest.TestCase):
    def test_normalise_audio_mime_rewrites_video_prefix(self):
        """MediaRecorder video/webm declarations must be normalized to audio/webm."""
        self.assertEqual(normalise_audio_mime("video/webm", "note.webm"), "audio/webm")
        self.assertEqual(normalise_audio_mime("video/mp4", "note.mp4"), "audio/mp4")
        self.assertEqual(normalise_audio_mime("audio/wav", "note.wav"), "audio/wav")
        self.assertEqual(normalise_audio_mime(None, "note.mp3"), "audio/mp3")

    def test_approve_task_transitions_status_increments_ladder_and_executes(self):
        """Approving a pending task updates status to approved, records ladder approval, and runs execution."""
        repo = FakeTaskRepository(
            {
                "task-1": {
                    "class": "make_call",
                    "task": "Call the plumber",
                    "status": "pending_approval",
                    "correlation_id": "cid-approve-1",
                }
            }
        )
        trust_engine = FakeTrustEngine()
        orchestrator = TaskOrchestrator(repo, FakeParser())
        orchestrator.trust_engine = trust_engine

        with patch(
            "src.domain.orchestrator.run_for_task",
            return_value={"execution_status": "draft_ready"},
        ) as mock_run:
            res = orchestrator.approve("task-1")

        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["execution"], {"execution_status": "draft_ready"})
        self.assertEqual(repo.tasks["task-1"]["status"], "approved")
        self.assertEqual(len(trust_engine.approvals_recorded), 1)
        self.assertEqual(
            trust_engine.approvals_recorded[0], ("make_call", "cid-approve-1")
        )
        mock_run.assert_called_once_with(
            repo,
            "task-1",
            {
                "class": "make_call",
                "task": "Call the plumber",
                "status": "pending_approval",
                "correlation_id": "cid-approve-1",
                "id": "task-1",
            },
            "cid-approve-1",
        )

    def test_reject_auto_approved_task_triggers_demotion(self):
        """Rejecting an auto_approved task must record a trust ladder demotion."""
        repo = FakeTaskRepository(
            {
                "task-auto": {
                    "class": "research",
                    "task": "Check AWS migration",
                    "status": "auto_approved",
                    "correlation_id": "cid-reject-1",
                }
            }
        )
        trust_engine = FakeTrustEngine()
        orchestrator = TaskOrchestrator(repo, FakeParser())
        orchestrator.trust_engine = trust_engine

        res = orchestrator.reject("task-auto")

        self.assertEqual(res["status"], "ok")
        self.assertEqual(repo.tasks["task-auto"]["status"], "rejected")
        self.assertEqual(len(trust_engine.demotions_recorded), 1)
        self.assertEqual(
            trust_engine.demotions_recorded[0], ("research", "cid-reject-1")
        )

    def test_reject_pending_task_does_not_demote(self):
        """Rejecting a regular pending task updates status to rejected without resetting ladder."""
        repo = FakeTaskRepository(
            {
                "task-pending": {
                    "class": "message_person",
                    "task": "Send email",
                    "status": "pending_approval",
                    "correlation_id": "cid-reject-2",
                }
            }
        )
        trust_engine = FakeTrustEngine()
        orchestrator = TaskOrchestrator(repo, FakeParser())
        orchestrator.trust_engine = trust_engine

        res = orchestrator.reject("task-pending")

        self.assertEqual(res["status"], "ok")
        self.assertEqual(repo.tasks["task-pending"]["status"], "rejected")
        self.assertEqual(len(trust_engine.demotions_recorded), 0)

    def test_evaluate_deferred_promotes_met_condition_and_skips_rejected(self):
        """Deferred evaluation promotes met conditions, re-defers unmet, and processes tasks."""
        repo = FakeTaskRepository()
        deferred_tasks = [
            # Met condition (flight below 15000)
            {
                "id": "t-met",
                "task": "Flight below 15000",
                "status": "pending_approval",
                "condition": "flight < 15000",
                "correlation_id": "c1",
            },
            # Unmet condition
            {
                "id": "t-unmet",
                "task": "Weather is raining",
                "status": "pending_approval",
                "condition": "temperature > 100",
                "correlation_id": "c2",
            },
        ]
        repo.list_deferred_ready = MagicMock(return_value=deferred_tasks)

        trust_engine = FakeTrustEngine()
        orchestrator = TaskOrchestrator(repo, FakeParser())
        orchestrator.trust_engine = trust_engine

        # evaluator returns True for flight < 15000, False for temperature > 100
        orchestrator._evaluator.evaluate = MagicMock(
            side_effect=lambda cond: "15000" in cond
        )

        res = orchestrator.evaluate_deferred()

        self.assertEqual(res["status"], "ok")
        self.assertEqual(res["processed"], 2)
        self.assertEqual(
            res["results"],
            [
                {"id": "t-met", "action": "promoted"},
                {"id": "t-unmet", "action": "re-deferred"},
            ],
        )

    def test_process_voice_note_computes_and_returns_summary(self):
        """process_voice_note must compute and return summary for UI and spoken confirmation."""
        repo = FakeTaskRepository()
        repo.create = MagicMock(
            side_effect=lambda doc: (
                f"id-{doc['task']}",
                dict(doc, id=f"id-{doc['task']}"),
            )
        )
        tasks = [
            {"task": "Send message", "lane": "now", "class": "message_person"},
            {"task": "Do research", "lane": "next", "class": "research"},
            {
                "task": "Watch flight",
                "lane": "later",
                "class": "watch_price",
                "condition": "flight < 100",
            },
        ]
        parser = FakeParser(tasks=tasks)
        trust_engine = FakeTrustEngine(default_status="pending_approval")
        orchestrator = TaskOrchestrator(repo, parser)
        orchestrator.trust_engine = trust_engine

        with patch("builtins.open", unittest.mock.mock_open(read_data=b"fake-audio")):
            res = orchestrator.process_voice_note("fake.wav", "cid-summary-test")

        self.assertIn("summary", res)
        summary = res["summary"]
        self.assertEqual(summary["total"], 3)
        self.assertEqual(summary["pending"], 3)
        self.assertEqual(summary["watching"], 1)
        self.assertEqual(summary["correlation_id"], "cid-summary-test")


if __name__ == "__main__":
    unittest.main()
