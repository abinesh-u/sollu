"""Shared application-level singletons.

Built once at import time. Both main.py and agent.py import from here so
there is exactly one Firestore client, one TaskRepository, and one
TaskOrchestrator for the lifetime of the process — one trust ladder, one
set of approval counts, one connection pool.
"""
import os
from dotenv import dotenv_values
from google.cloud import firestore

from src.domain.orchestrator import TaskOrchestrator
from src.domain.parser import GeminiAudioParser
from src.domain.task_repo import TaskRepository

cfg = dotenv_values(".env")
project = cfg.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
db = firestore.Client(project=project)
repo = TaskRepository(db)
orchestrator = TaskOrchestrator(repo, GeminiAudioParser())
