"""Single place that constructs the Vertex genai client.

Both the triage parser and the executors need a client against the same project
and the same `global` model endpoint (locked in AGENTS.md). Keeping one builder
means there is no second config path to drift.
"""
import os

from dotenv import dotenv_values
from google import genai
from google.genai import types


def vertex_client(timeout_ms: int | None = None) -> genai.Client:
    """Build a Vertex genai client.

    `.env` wins locally; on Cloud Run there is no `.env`, so the process
    environment supplies the same two values.
    """
    cfg = dotenv_values(".env")
    project = cfg.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = (cfg.get("GOOGLE_CLOUD_LOCATION")
                or os.environ.get("GOOGLE_CLOUD_LOCATION")
                or "global")

    kwargs = {}
    if timeout_ms is not None:
        kwargs["http_options"] = types.HttpOptions(timeout=timeout_ms)

    return genai.Client(vertexai=True, project=project, location=location, **kwargs)
