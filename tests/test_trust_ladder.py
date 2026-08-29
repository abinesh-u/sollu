import unittest
from unittest.mock import MagicMock
from google.cloud import firestore
from src.domain.trust_ladder import TrustLadderEngine


class FakeDocumentSnapshot:
    def __init__(self, doc_id, data):
        self.id = doc_id
        self._data = data

    @property
    def exists(self):
        return self._data is not None

    def to_dict(self):
        return dict(self._data) if self._data else {}


class FakeDocumentReference:
    def __init__(self, collection, doc_id):
        self.collection = collection
        self.doc_id = doc_id

    def get(self):
        data = self.collection.docs.get(self.doc_id)
        return FakeDocumentSnapshot(self.doc_id, data)

    def set(self, fields, merge=False):
        current = self.collection.docs.get(self.doc_id) or {}
        for k, v in fields.items():
            if isinstance(v, firestore.Increment):
                inc_val = getattr(v, "value", 1)
                current[k] = current.get(k, 0) + inc_val
            else:
                current[k] = v
        self.collection.docs[self.doc_id] = current


class FakeCollectionReference:
    def __init__(self, name):
        self.name = name
        self.docs = {}
        self.added = []

    def document(self, doc_id):
        return FakeDocumentReference(self, doc_id)

    def stream(self):
        for doc_id, data in list(self.docs.items()):
            yield FakeDocumentSnapshot(doc_id, data)

    def add(self, data):
        self.added.append(data)
        doc_id = f"auto-{len(self.added)}"
        self.docs[doc_id] = data
        return None, FakeDocumentReference(self, doc_id)


class FakeFirestoreClient:
    def __init__(self):
        self.collections = {}

    def collection(self, name):
        if name not in self.collections:
            self.collections[name] = FakeCollectionReference(name)
        return self.collections[name]


class TestTrustLadderEngine(unittest.TestCase):
    def setUp(self):
        self.db = FakeFirestoreClient()
        self.engine = TrustLadderEngine(self.db)

    def test_new_task_starts_as_pending_approval(self):
        """Tasks with 0 approvals must evaluate to pending_approval."""
        status = self.engine.get_status_for_task("research", correlation_id="cid-1")
        self.assertEqual(status, "pending_approval")

    def test_reaching_three_approvals_promotes_and_records_event(self):
        """Recording 3 approvals must cross threshold to auto_approved and write promotion_events."""
        self.engine.record_approval("research", "cid-1")
        self.assertEqual(self.engine.get_status_for_task("research", "cid-1"), "pending_approval")

        self.engine.record_approval("research", "cid-2")
        self.assertEqual(self.engine.get_status_for_task("research", "cid-2"), "pending_approval")

        # Third approval crosses threshold (3)
        self.engine.record_approval("research", "cid-3")
        self.assertEqual(self.engine.get_status_for_task("research", "cid-3"), "auto_approved")

        # Verify promotion event was written
        events = self.db.collection("promotion_events").added
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["class"], "research")
        self.assertEqual(events[0]["count"], 3)

    def test_demotion_resets_approvals_to_zero(self):
        """Rejecting an auto-approved task resets approvals to 0 and reverts status to pending_approval."""
        # Setup class with 3 approvals
        for i in range(3):
            self.engine.record_approval("watch_price", f"cid-{i}")
        self.assertEqual(self.engine.get_status_for_task("watch_price", "cid-check"), "auto_approved")

        # Demote
        self.engine.record_demotion("watch_price", "cid-demote")
        self.assertEqual(self.engine.get_status_for_task("watch_price", "cid-after"), "pending_approval")
        self.assertEqual(self.engine.get_all_approvals(["watch_price"])["watch_price"], 0)

    def test_get_all_approvals_seeds_known_classes_at_zero(self):
        """All known classes must be present in the ladder dictionary even if never stored."""
        self.engine.record_approval("make_call", "cid-1")
        ladder = self.engine.get_all_approvals(["make_call", "message_person", "research"])

        self.assertEqual(ladder["make_call"], 1)
        self.assertEqual(ladder["message_person"], 0)
        self.assertEqual(ladder["research"], 0)


if __name__ == "__main__":
    unittest.main()
