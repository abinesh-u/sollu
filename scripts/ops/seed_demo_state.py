from google.cloud import firestore


def seed_demo_state():
    """Sets the Trust Ladder to the perfect state for the demo video."""
    print("Seeding Firestore Trust Ladder for the Demo Video...")
    db = firestore.Client(project="sixth-radar-506906-i1", database="(default)")

    ladder_ref = db.collection("trust_ladder")

    # 1. Soft Task at 2/3 approvals (ready to be promoted live on video)
    ladder_ref.document("create_notion_page").set({"approvals": 2})
    print("✅ Set 'create_notion_page' approvals to 2 (Ready for promotion!)")

    # 2. Hard Task at 5 approvals (proves that it NEVER auto-executes)
    ladder_ref.document("send_email").set({"approvals": 5})
    # Also set message_person to 5 if message_person is considered a hard task,
    # but based on the code message_person is a draft/soft task. Let's set it to 0.

    # 3. Soft task at 0 (baseline)
    ladder_ref.document("make_call").set({"approvals": 0})
    ladder_ref.document("message_person").set({"approvals": 0})
    print("✅ Set baseline approvals to 0")

    # Clear old promotion events to keep logs clean
    events = db.collection("promotion_events").stream()
    count = 0
    for doc in events:
        doc.reference.delete()
        count += 1
    print(f"🧹 Cleared {count} old promotion events.")

    print("\n🎉 Demo state seeded! The UI is ready for the video.")


if __name__ == "__main__":
    seed_demo_state()
