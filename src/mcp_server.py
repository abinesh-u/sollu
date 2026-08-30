import os
import base64
from email.message import EmailMessage
from mcp.server.mcpserver import MCPServer
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

mcp = MCPServer("voice_agent_mcp")

def get_google_creds():
    if os.path.exists('token.json'):
        return Credentials.from_authorized_user_file('token.json')
    return None

# --- WRITE TOOLS ---

@mcp.tool()
def send_email(to_email: str, subject: str, body: str) -> str:
    """Send an email using Gmail. You MUST use an exact email address. Do not guess."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    try:
        service = build('gmail', 'v1', credentials=creds)
        message = EmailMessage()
        message.set_content(body)
        message['To'] = to_email
        message['From'] = 'me'
        message['Subject'] = subject

        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
        create_message = {'raw': encoded_message}
        
        send_message = (service.users().messages().send(userId="me", body=create_message).execute())
        return f"Message Id: {send_message['id']}"
    except Exception as e:
        return f"Failed to send email: {str(e)}"

@mcp.tool()
def add_todo_task(title: str, notes: str = "") -> str:
    """Add a task to the default Google Tasks list."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    try:
        service = build('tasks', 'v1', credentials=creds)
        task = {
            'title': title,
            'notes': notes
        }
        result = service.tasks().insert(tasklist='@default', body=task).execute()
        return f"Task Id: {result['id']}"
    except Exception as e:
        return f"Failed to add task: {str(e)}"

@mcp.tool()
def log_expense(amount: float, category: str, vendor: str, date: str) -> str:
    """Log an expense to a Google Sheet."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    sheet_id = os.getenv("EXPENSE_SHEET_ID")
    if not sheet_id: return "Error: EXPENSE_SHEET_ID not set."
    try:
        service = build('sheets', 'v4', credentials=creds)
        values = [[date, vendor, category, amount]]
        result = service.spreadsheets().values().append(
            spreadsheetId=sheet_id, range="Sheet1!A:D", valueInputOption="USER_ENTERED", body={'values': values}
        ).execute()
        return f"Updated Range: {result.get('updates', {}).get('updatedRange', 'unknown')}"
    except Exception as e:
        return f"Failed to log expense: {str(e)}"

@mcp.tool()
def create_calendar_event(title: str, start_time_iso: str, end_time_iso: str) -> str:
    """Create an event on the primary Google Calendar."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    try:
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': title,
            'start': {'dateTime': start_time_iso, 'timeZone': 'UTC'},
            'end': {'dateTime': end_time_iso, 'timeZone': 'UTC'},
        }
        event_result = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event Link: {event_result.get('htmlLink')}"
    except Exception as e:
        return f"Failed to create event: {str(e)}"

@mcp.tool()
def append_to_doc(text: str) -> str:
    """Append text to the brain dump Google Doc."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    doc_id = os.getenv("BRAIN_DUMP_DOC_ID")
    if not doc_id: return "Error: BRAIN_DUMP_DOC_ID not set."
    try:
        service = build('docs', 'v1', credentials=creds)
        requests = [{"insertText": {"location": {"index": 1}, "text": text + "\n"}}]
        result = service.documents().batchUpdate(documentId=doc_id, body={'requests': requests}).execute()
        return f"Revision ID: {result.get('documentId')}"
    except Exception as e:
        return f"Failed to append to doc: {str(e)}"

# --- READ TOOLS ---

@mcp.tool()
def lookup_contact(name: str) -> str:
    """Search Google Contacts by name to find an email address."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    try:
        service = build('people', 'v1', credentials=creds)
        results = service.people().searchContacts(query=name, readMask='names,emailAddresses').execute()
        connections = results.get('results', [])
        if not connections:
            return f"No contact found for {name}."
        
        found = []
        for person_match in connections:
            person = person_match.get('person', {})
            emails = person.get('emailAddresses', [])
            if emails:
                found.append(emails[0].get('value'))
        return f"Found emails: {', '.join(found)}"
    except Exception as e:
        return f"Failed to lookup contact: {str(e)}"

@mcp.tool()
def list_tasks() -> str:
    """List recent tasks in the default Google Tasks list to check for duplicates."""
    creds = get_google_creds()
    if not creds: return "Error: token.json not found."
    try:
        service = build('tasks', 'v1', credentials=creds)
        results = service.tasks().list(tasklist='@default', maxResults=10).execute()
        items = results.get('items', [])
        if not items:
            return "No tasks found."
        return "\n".join([f"- {task['title']} (ID: {task['id']})" for task in items])
    except Exception as e:
        return f"Failed to list tasks: {str(e)}"
