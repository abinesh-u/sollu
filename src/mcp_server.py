import base64
import os
from email.message import EmailMessage

from google.auth.transport.requests import Request
from google.cloud import firestore
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("voice_agent_mcp")
_cached_refresh_token = None


def get_google_creds():
    global _cached_refresh_token

    client_id = os.environ.get("GOOGLE_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

    if not client_id or not client_secret:
        return None

    if not _cached_refresh_token:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project)
        doc = db.collection("oauth_tokens").document("default_user").get()
        if doc.exists:
            _cached_refresh_token = doc.to_dict().get("refresh_token")

    if not _cached_refresh_token:
        return None

    creds = Credentials(
        token=None,
        refresh_token=_cached_refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri="https://oauth2.googleapis.com/token",
        scopes=[
            "https://www.googleapis.com/auth/gmail.compose",
            "https://www.googleapis.com/auth/gmail.send",
            "https://www.googleapis.com/auth/tasks",
        ],
    )
    creds.refresh(Request())
    return creds


# --- WRITE TOOLS ---


@mcp.tool()
def send_email(to_email: str, subject: str, body: str, is_draft: bool = False) -> str:
    """Send or draft an email using Gmail. You MUST use an exact email address. Do not guess."""
    creds = get_google_creds()
    if not creds:
        # Graceful degradation (Tier 1 mode): Simulate success so the ladder keeps working.
        mode = "Drafted" if is_draft else "Sent"
        return f"{mode} email to {to_email} (Subject: {subject}). [No credentials - simulation mode]"

    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()
        message.set_content(body)
        message["To"] = to_email
        message["From"] = "me"
        message["Subject"] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {"message": {"raw": encoded_message}}

        if is_draft:
            created_draft = (
                service.users()
                .drafts()
                .create(userId="me", body=create_message)
                .execute()
            )
            return f"Draft created: {created_draft['id']}"
        else:
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body={"raw": encoded_message})
                .execute()
            )
            return f"Message Id: {send_message['id']}"
    except Exception as e:
        return f"Failed to send email: {e!s}"


@mcp.tool()
def add_todo_task(title: str, notes: str = "") -> str:
    """Add a task to the default Google Tasks list."""
    creds = get_google_creds()
    if not creds:
        return f"Task queued: '{title}'. [No credentials - simulation mode]"

    try:
        service = build("tasks", "v1", credentials=creds)
        task = {"title": title, "notes": notes}
        result = service.tasks().insert(tasklist="@default", body=task).execute()
        return f"Task Id: {result['id']}"
    except Exception as e:
        return f"Failed to add task: {e!s}"


@mcp.tool()
def create_notion_page(title: str, content: str = "") -> str:
    """Create a new page in the default Notion database with the given title and content."""
    api_key = os.environ.get("NOTION_API_KEY")
    db_id = os.environ.get("NOTION_DATABASE_ID")

    if not api_key or not db_id:
        return f"Notion page queued: '{title}'. [No credentials - simulation mode]"

    import httpx

    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28",
    }

    data = {
        "parent": {"database_id": db_id},
        "properties": {"Name": {"title": [{"text": {"content": title}}]}},
    }

    if content:
        data["children"] = [
            {
                "object": "block",
                "type": "paragraph",
                "paragraph": {
                    "rich_text": [{"type": "text", "text": {"content": content}}]
                },
            }
        ]

    try:
        response = httpx.post(url, headers=headers, json=data, timeout=10.0)
        response.raise_for_status()
        return f"Notion Page Created: {response.json().get('id')}"
    except httpx.HTTPStatusError as e:
        return f"Failed to create Notion page: HTTP {e.response.status_code} - {e.response.text}"
    except Exception as e:
        return f"Failed to create Notion page: {e!s}"


# --- READ TOOLS ---


@mcp.tool()
def list_tasks() -> str:
    """List recent tasks in the default Google Tasks list to check for duplicates."""
    creds = get_google_creds()
    if not creds:
        return "No credentials - returning empty task list simulation."

    try:
        service = build("tasks", "v1", credentials=creds)
        results = service.tasks().list(tasklist="@default", maxResults=10).execute()
        items = results.get("items", [])
        if not items:
            return "No tasks found."
        return "\n".join([f"- {task['title']} (ID: {task['id']})" for task in items])
    except Exception as e:
        return f"Failed to list tasks: {e!s}"
