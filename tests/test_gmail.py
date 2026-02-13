"""Test Gmail API connection."""
import sys
import os

# Add parent directory to path to import src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.gmail import get_gmail_service


def main():
    """Test Gmail API access."""
    service = get_gmail_service()
    results = service.users().messages().list(
        userId="me",
        labelIds=["INBOX"],
        maxResults=5,
        q="is:unread"
    ).execute()
    
    msgs = results.get("messages", [])
    print(f"Unread sample count returned: {len(msgs)}")
    
    if msgs:
        m = service.users().messages().get(
            userId="me",
            id=msgs[0]["id"],
            format="metadata"
        ).execute()
        headers = {h["name"]: h["value"] for h in m["payload"].get("headers", [])}
        print("Top unread subject:", headers.get("Subject"))


if __name__ == "__main__":
    main()
