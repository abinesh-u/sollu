"""Reset Firestore to a known state for the demo recording.

Clears every task, ladder entry, and promotion event, then rebuilds state by
running real voice notes through the orchestrator — so nothing on screen is a
seeded number. Leaves `make_call` at 2 approvals with a third make_call task
still pending, so approving it on camera crosses the threshold live.

Usage:
    uv run python scripts/reset_demo.py
    uv run python scripts/reset_demo.py --clear-only
    uv run python scripts/reset_demo.py --notes 3 --audio /path/to/note.wav
"""
import argparse
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from dotenv import dotenv_values
from google.cloud import firestore

from src.domain.orchestrator import TaskOrchestrator
from src.domain.parser import GeminiAudioParser
from src.domain.trust_ladder import TrustLadderEngine

COLLECTIONS = ["tasks", "trust_ladder", "promotion_events"]
PROMOTE_CLASS = "make_call"


def clear(db):
    for name in COLLECTIONS:
        n = 0
        for doc in db.collection(name).stream():
            doc.reference.delete()
            n += 1
        print(f"  cleared {name}: {n} docs")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", default="/tmp/voice-test/positive.wav")
    ap.add_argument("--notes", type=int, default=3,
                    help="voice notes to process; needs >= 3 to leave one make_call pending")
    ap.add_argument("--clear-only", action="store_true")
    args = ap.parse_args()

    cfg = dotenv_values(".env")
    db = firestore.Client(project=cfg.get("GOOGLE_CLOUD_PROJECT"))

    print("Clearing collections...")
    clear(db)
    if args.clear_only:
        print("Done (clear only). Every class starts at zero.")
        return

    audio = Path(args.audio)
    if not audio.exists():
        sys.exit(f"audio not found: {audio}")

    orchestrator = TaskOrchestrator(db, GeminiAudioParser())
    print(f"\nProcessing {args.notes} voice note(s) from {audio.name}...")
    for i in range(args.notes):
        result = orchestrator.process_voice_note(str(audio), str(uuid.uuid4()))
        print(f"  note {i + 1}: {len(result['tasks'])} tasks, "
              f"{result['usage']['total']} tokens")

    # Approve all but one task of the promote class, using the real ladder engine.
    engine = TrustLadderEngine(db)
    pending = [d for d in db.collection("tasks").stream()
               if d.to_dict().get("class") == PROMOTE_CLASS
               and d.to_dict().get("status") == "pending_approval"]

    if len(pending) < engine.AUTO_EXECUTE_THRESHOLD:
        print(f"\n! only {len(pending)} '{PROMOTE_CLASS}' tasks — need "
              f"{engine.AUTO_EXECUTE_THRESHOLD} to stage the live promotion. "
              f"Re-run with --notes {engine.AUTO_EXECUTE_THRESHOLD}.")

    to_approve = pending[:engine.AUTO_EXECUTE_THRESHOLD - 1]
    for doc in to_approve:
        doc.reference.update({"status": "approved"})
        engine.record_approval(PROMOTE_CLASS, f"demo-reset-{doc.id}")

    ladder = {d.id: d.to_dict().get("approvals", 0)
              for d in db.collection("trust_ladder").stream()}
    print(f"\nLadder: {ladder or '(all classes at zero)'}")
    print(f"'{PROMOTE_CLASS}' at {ladder.get(PROMOTE_CLASS, 0)}/"
          f"{engine.AUTO_EXECUTE_THRESHOLD} — approving the remaining "
          f"{len(pending) - len(to_approve)} on camera promotes it live.")


if __name__ == "__main__":
    main()
