import json
import sys

def log_event(correlation_id: str, event: str, **kwargs):
    """
    Structured JSON logger writing directly to stdout.
    This provides zero-dependency observability tailored for GCP Cloud Logging.
    """
    log_data = {
        "correlation_id": correlation_id,
        "event": event,
    }
    log_data.update(kwargs)
    print(json.dumps(log_data), flush=True)
