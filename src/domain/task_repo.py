"""Task persistence behind one seam.

Every Firestore read and write for the `tasks` collection goes through here.
Callers never see collection names, field name strings, SERVER_TIMESTAMP, or
the in-memory filter workaround for deferred tasks. Change a field name or
a query shape → change one file.
"""
from google.cloud import firestore
from datetime import datetime, timezone


class TaskRepository:
    def __init__(self, db: firestore.Client):
        self._db = db
        self._col = db.collection("tasks")

    def create(self, doc_data: dict) -> tuple[str, dict]:
        """Persist a new task document.

        Returns (document_id, doc_data_with_id) so the caller can include the
        ID in its response without a second read.
        """
        _, doc_ref = self._col.add(doc_data)
        doc_data["id"] = doc_ref.id
        # SERVER_TIMESTAMP is a sentinel, not serialisable — replace with a
        # wall-clock value for the response payload only.
        doc_data["created_at"] = datetime.now(timezone.utc).isoformat()
        return doc_ref.id, doc_data

    def get_or_raise(self, task_id: str) -> dict:
        """Fetch a task by ID, raising ValueError if missing."""
        doc = self._col.document(task_id).get()
        if not doc.exists:
            raise ValueError(f"Task {task_id} not found")
        data = doc.to_dict()
        data["id"] = doc.id
        return data

    def update(self, task_id: str, fields: dict) -> None:
        """Partial update on a task document."""
        self._col.document(task_id).update(fields)

    def update_execution(self, task_id: str, fields: dict) -> None:
        """Update task with execution results, stamping executed_at server-side."""
        payload = dict(fields)
        payload["executed_at"] = firestore.SERVER_TIMESTAMP
        self._col.document(task_id).update(payload)

    def delete(self, task_id: str) -> None:
        self.coll.document(task_id).delete()

    def list_recent(self, limit: int = 50) -> list[dict]:
        """Tasks ordered by created_at descending, serialised for JSON."""
        tasks = []
        docs = (self._col
                .order_by("created_at", direction=firestore.Query.DESCENDING)
                .limit(limit)
                .stream())
        for doc in docs:
            t = doc.to_dict()
            t["id"] = doc.id
            if "created_at" in t and hasattr(t["created_at"], "isoformat"):
                t["created_at"] = t["created_at"].isoformat()
            tasks.append(t)
        return tasks

    def list_deferred_ready(self, now_ts: float) -> list[dict]:
        """Later-lane tasks whose check_after has passed.

        Filters check_after in memory rather than in the query: a second
        range clause would need a composite Firestore index, and the later
        lane is small enough that fetching it whole is cheaper than the
        index it would cost to avoid.
        """
        ready = []
        docs = self._col.where("lane", "==", "later").stream()
        for doc in docs:
            data = doc.to_dict()
            data["id"] = doc.id
            if data.get("check_after", 0) <= now_ts:
                ready.append(data)
        return ready
