# Voice Agent Task Intents Blueprint

This document defines the fine-grained task classes (intents) for the voice agent, categorizing them by risk level. This structure supports the **trust ladder** system, allowing the AI to earn trust for low-risk tasks quickly while gating high-risk actions behind user permission (requiring 3 approvals for auto-execution).

## 1. Low Risk (Read-Only / Self-Directed Info)
These tasks involve fetching information without modifying any external state. They are ideal for rapid trust-building.

*   **`read_email`**: Summarize or read unread emails.
    *   *Source/Capability*: Google Workspace (Gmail API) - requires `https://www.googleapis.com/auth/gmail.readonly` scope.
*   **`check_calendar`**: Check schedule or upcoming meetings.
    *   *Source/Capability*: Google Workspace (Calendar API) - requires `https://www.googleapis.com/auth/calendar.readonly` scope.
*   **`search_drive`**: Find documents or files.
    *   *Source/Capability*: Google Workspace (Drive API) - requires `https://www.googleapis.com/auth/drive.readonly` scope.

## 2. Medium Risk (Drafts / Internal Modifications)
These tasks involve creating or modifying data but have low external impact. They are safe to auto-execute once trusted because the user can easily review or undo them.

*   **`draft_email`**: Draft an email without sending it (replaces `message_person` draft stub).
    *   *Source/Capability*: Google Workspace (Gmail API) - requires `https://www.googleapis.com/auth/gmail.compose` scope.
*   **`create_calendar_event`**: Schedule a meeting or time block.
    *   *Source/Capability*: Google Workspace (Calendar API) - requires `https://www.googleapis.com/auth/calendar.events` scope.
*   **`create_notion_page`**: Add a new note or task entry.
    *   *Source/Capability*: Notion API - requires Insert Content capability.
*   **`log_expense`**: Extract data to update a ledger or spreadsheet.
    *   *Data Fields*: `amount`, `category`, `vendor`, `date`
    *   *Target*: Google Sheets API / Notion API
*   **`add_shopping_item`**: Append items to a persistent digital list.
    *   *Data Fields*: `item_name`, `quantity`, `list_type` (e.g., Groceries, Hardware)
    *   *Target*: Google Keep API / Todoist API
*   **`capture_raw_brain_dump`**: Save unorganized thoughts into a general journal note.
    *   *Data Fields*: `raw_text`, `timestamp`
    *   *Target*: Google Docs API / Apple Notes

## 3. High Risk (External Actions / Destructive Operations)
These tasks involve external communications or permanent data changes. They should strictly require user permission until significant trust is established (and may demote to zero if rejected).

*   **`send_email`**: Send an email directly to a recipient.
    *   *Source/Capability*: Google Workspace (Gmail API) - requires `https://www.googleapis.com/auth/gmail.send` scope.
*   **`share_drive_file`**: Change permissions on a file to share it externally.
    *   *Source/Capability*: Google Workspace (Drive API) - requires `https://www.googleapis.com/auth/drive` or specific file scopes.
*   **`delete_drive_file`**: Move a file to trash or permanently delete it.
    *   *Source/Capability*: Google Workspace (Drive API) - requires `https://www.googleapis.com/auth/drive` scope.
*   **`delete_notion_page`**: Archive or trash a Notion page/database.
    *   *Source/Capability*: Notion API - requires Delete/Trash capabilities.

### References
*   [Google Workspace API Documentation & Scopes](https://developers.google.com/workspace)
*   [Notion API Developer Portal & Capabilities](https://developers.notion.com)
