import json
from google.cloud import firestore
from datetime import datetime, timezone
import os
from dotenv import dotenv_values

cfg = dotenv_values(".env")
db = firestore.Client(project=cfg.get("GOOGLE_CLOUD_PROJECT"))

tasks = [
    {"task": "Call the plumber", "lane": "now", "class": "make_call", "status": "pending_approval"},
    {"task": "Send a loom video to Ravi before the standup", "lane": "now", "class": "message_person", "status": "pending_approval"},
    {"task": "Look into whether the cloud SQL migration is worth it", "lane": "next", "class": "research", "status": "pending_approval"},
    {"task": "Check if flight to Bangalore drops below 15,000 rupees", "lane": "next", "class": "watch_price", "status": "auto_approved"},
    {"task": "Redo the onboarding flow", "lane": "later", "class": "other", "status": "pending_approval"}
]

# Set trust ladder
db.collection("trust_ladder").document("watch_price").set({"approvals": 4}, merge=True)
db.collection("trust_ladder").document("make_call").set({"approvals": 2}, merge=True)

# Add tasks
for t in tasks:
    t["created_at"] = firestore.SERVER_TIMESTAMP
    db.collection("tasks").add(t)

print("Mock data seeded!")
