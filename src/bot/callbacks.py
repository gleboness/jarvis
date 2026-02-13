"""Callback handlers for inline keyboard buttons."""
from telegram import Update
from telegram.ext import ContextTypes

from src.config import ALLOWED_USER_IDS
from src.database import SessionLocal, PendingEmailDraft
from src.gmail import (
    get_message,
    mark_as_read,
    create_reply_draft,
    send_draft,
    delete_draft,
    batch_mark_as_spam,
)
from src.llm import LLMClient
from .prompts import EMAIL_DRAFT_PROMPT_TEMPLATE

# Temporary storage for pending spam confirmations
PENDING_SPAM = {}  # telegram_user_id -> [message_id, ...]


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries from inline keyboards."""
    query = update.callback_query
    await query.answer()
    
    if not query or not query.data:
        return
    
    user = update.effective_user
    if not user or user.id not in ALLOWED_USER_IDS:
        return

    action, item_id = query.data.split(":", 1)

    # Spam sweep confirmation
    if action == "spamconfirm":
        await handle_spam_confirmation(query, item_id)
        return
    
    # Mark as read
    if action == "read":
        await handle_mark_read(query, item_id)
        return
    
    # Draft reply
    if action == "draft":
        await handle_draft_reply(query, item_id, context)
        return
    
    # Send/Discard draft
    if action in ("send", "discard"):
        await handle_draft_action(query, action, item_id)
        return
    
    await query.message.reply_text("Unknown action.")


async def handle_spam_confirmation(query, item_id: str):
    """Handle spam sweep confirmation."""
    user_id = query.from_user.id
    
    if item_id == "no":
        PENDING_SPAM.pop(user_id, None)
        await query.edit_message_text("Canceled.")
        return
    
    ids = PENDING_SPAM.pop(user_id, [])
    if not ids:
        await query.edit_message_text("Nothing pending.")
        return
    
    try:
        batch_mark_as_spam(ids)
        await query.edit_message_text(f"Moved {len(ids)} messages to Spam.")
    except Exception as e:
        await query.edit_message_text(f"Failed to move to Spam: {e}")


async def handle_mark_read(query, message_id: str):
    """Handle marking message as read."""
    try:
        mark_as_read(message_id)
        await query.edit_message_reply_markup(reply_markup=None)
        await query.message.reply_text("Marked as read.")
    except Exception as e:
        await query.message.reply_text(f"Failed to mark as read: {e}")


async def handle_draft_reply(query, message_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Handle creating a draft reply."""
    user_id = query.from_user.id
    
    # Get email details
    headers, snippet, label_ids = get_message(message_id)
    subj = headers.get("Subject", "(no subject)")
    frm = headers.get("From", "(unknown)")
    
    # Generate reply using LLM
    llm_client: LLMClient = context.bot_data.get("llm_client")
    prompt = EMAIL_DRAFT_PROMPT_TEMPLATE.format(subj=subj, frm=frm, snippet=snippet)
    reply_text = llm_client.call(user_id, prompt)
    
    # Create Gmail draft
    draft = create_reply_draft(message_id, reply_text)
    draft_id = draft["id"]
    
    # Store pending approval in database
    db = SessionLocal()
    try:
        db.add(PendingEmailDraft(
            telegram_user_id=str(user_id),
            message_id=message_id,
            draft_id=draft_id,
            draft_text=reply_text
        ))
        db.commit()
    finally:
        db.close()
    
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("Approve & Send", callback_data=f"send:{draft_id}"),
        InlineKeyboardButton("Discard (delete draft)", callback_data=f"discard:{draft_id}"),
    ]])
    
    await query.message.reply_text(
        f"Draft created (NOT sent).\n\n---\n{reply_text}\n---",
        reply_markup=kb
    )


async def handle_draft_action(query, action: str, draft_id: str):
    """Handle sending or discarding a draft."""
    user_id = query.from_user.id
    
    db = SessionLocal()
    try:
        row = db.query(PendingEmailDraft).filter(PendingEmailDraft.draft_id == draft_id).first()
        if not row:
            await query.edit_message_text("This draft is no longer pending.")
            return
        
        if str(user_id) != row.telegram_user_id:
            await query.edit_message_text("Not authorized for this draft.")
            return
        
        if action == "send":
            send_draft(draft_id)
            # After sending, mark the original email as read
            try:
                mark_as_read(row.message_id)
            except Exception:
                pass
            
            db.delete(row)
            db.commit()
            await query.edit_message_text("Sent.")
            return
        
        if action == "discard":
            # Delete the actual Gmail draft
            try:
                delete_draft(draft_id)
            except Exception:
                pass  # Even if deletion fails, clear local state
            
            db.delete(row)
            db.commit()
            await query.edit_message_text("Discarded and deleted from Gmail drafts.")
            return
    finally:
        db.close()
