"""Shared application-level singletons.

Built once at import time. Both main.py and agent.py import from here so
there is exactly one Firestore client, one TaskRepository, and one
TaskOrchestrator for the lifetime of the process — one trust ladder, one
set of approval counts, one connection pool.
"""
from dotenv import dotenv_values
from google.cloud import firestore

from src.domain.orchestrator import TaskOrchestrator
from src.domain.parser import GeminiAudioParser
from src.domain.task_repo import TaskRepository

cfg = dotenv_values(".env")
db = firestore.Client(project=cfg.get("GOOGLE_CLOUD_PROJECT"))
repo = TaskRepository(db)
orchestrator = TaskOrchestrator(repo, GeminiAudioParser())
