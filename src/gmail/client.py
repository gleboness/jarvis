"""Gmail API client."""
import base64
import os
from email.message import EmailMessage
from typing import Dict, Any, List, Tuple

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
import google.oauth2.credentials

from src.config import GMAIL_TOKEN_FILE, GMAIL_CREDS_FILE, GMAIL_SCOPES


def get_gmail_service():
    """Get authenticated Gmail API service."""
    creds = None
    if os.path.exists(GMAIL_TOKEN_FILE):
        creds = google.oauth2.credentials.Credentials.from_authorized_user_file(
            GMAIL_TOKEN_FILE, GMAIL_SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GMAIL_CREDS_FILE, GMAIL_SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GMAIL_TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def _headers_map(msg: Dict[str, Any]) -> Dict[str, str]:
    """Extract headers from Gmail message as dict."""
    headers = msg.get("payload", {}).get("headers", []) or []
    return {h["name"]: h["value"] for h in headers}


def list_unread(max_results: int = 10) -> List[Dict[str, Any]]:
    """List unread messages in inbox."""
    svc = get_gmail_service()
    res = svc.users().messages().list(
        userId="me",
        q="is:unread in:inbox",
        maxResults=max_results
    ).execute()
    return res.get("messages", []) or []


def get_message(message_id: str) -> Tuple[Dict[str, str], str, List[str]]:
    """Get message headers, snippet, and label IDs."""
    svc = get_gmail_service()
    msg = svc.users().messages().get(userId="me", id=message_id, format="metadata").execute()
    headers = _headers_map(msg)
    snippet = msg.get("snippet", "")
    label_ids = msg.get("labelIds", []) or []
    return headers, snippet, label_ids


def batch_mark_as_spam(message_ids: List[str]) -> None:
    """Move multiple messages to spam."""
    svc = get_gmail_service()
    svc.users().messages().batchModify(
        userId="me",
        body={
            "ids": message_ids,
            "addLabelIds": ["SPAM"],
            "removeLabelIds": ["INBOX", "UNREAD"],
        }
    ).execute()


def create_reply_draft(message_id: str, reply_body: str) -> Dict[str, Any]:
    """
    Creates a Gmail draft reply to an existing message.
    Uses the original 'From' as the To, and reuses Subject with Re: if needed.
    """
    svc = get_gmail_service()

    # Get metadata to build reply
    msg = svc.users().messages().get(userId="me", id=message_id, format="metadata").execute()
    headers = _headers_map(msg)
    to_addr = headers.get("Reply-To") or headers.get("From")
    subject = headers.get("Subject", "(no subject)")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    email = EmailMessage()
    email["To"] = to_addr
    email["Subject"] = subject
    email.set_content(reply_body)

    raw = base64.urlsafe_b64encode(email.as_bytes()).decode()
    draft = svc.users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()
    return draft  # contains draft['id']


def send_draft(draft_id: str) -> Dict[str, Any]:
    """Send a draft message."""
    svc = get_gmail_service()
    return svc.users().drafts().send(userId="me", body={"id": draft_id}).execute()


def delete_draft(draft_id: str) -> None:
    """Delete a draft message."""
    svc = get_gmail_service()
    svc.users().drafts().delete(userId="me", id=draft_id).execute()


def mark_as_read(message_id: str) -> None:
    """Mark a message as read."""
    svc = get_gmail_service()
    svc.users().messages().modify(
        userId="me",
        id=message_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()
