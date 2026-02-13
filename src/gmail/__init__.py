"""Gmail integration."""
from .client import (
    list_unread,
    get_message,
    create_reply_draft,
    send_draft,
    delete_draft,
    mark_as_read,
    batch_mark_as_spam,
)
from .triage import triage_email, gmail_fastpath_label

__all__ = [
    "list_unread",
    "get_message",
    "create_reply_draft",
    "send_draft",
    "delete_draft",
    "mark_as_read",
    "batch_mark_as_spam",
    "triage_email",
    "gmail_fastpath_label",
]
