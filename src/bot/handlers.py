"""Command and message handlers for the Telegram bot."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    MessageHandler,
    filters,
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
)

from src.config import ALLOWED_USER_IDS, GROUP_MODE
from src.gmail import list_unread, get_message
from src.gmail.triage import triage_email
from src.llm import LLMClient
from .callbacks import on_callback, PENDING_SPAM
from .news_handlers import news_cmd, channels_cmd, search_cmd, news_search_cmd


def allowed(update: Update) -> bool:
    """Check if user is allowed to use the bot."""
    user = update.effective_user
    return user and user.id in ALLOWED_USER_IDS


def should_respond_in_chat(update: Update, text: str, bot_username: str) -> bool:
    """Determine if bot should respond to a message in a chat."""
    chat = update.effective_chat
    if not chat or not text:
        return False
    if chat.type == "private":
        return True

    if GROUP_MODE == "off":
        return False
    if GROUP_MODE == "mentions":
        return f"@{bot_username}".lower() in text.lower()
    if GROUP_MODE == "commands":
        return text.strip().startswith("/jarvis")
    return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    if not allowed(update):
        return
    await update.message.reply_text("Jarvis online. Message me or mention me in a group.")


async def spam_sweep_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /spam_sweep command - scan inbox for spam."""
    if not allowed(update):
        return
    
    user_id = update.effective_user.id
    llm_client: LLMClient = context.bot_data.get("llm_client")
    
    msgs = list_unread(max_results=50)
    spam_ids = []
    examples = []
    
    for m in msgs:
        message_id = m["id"]
        headers, snippet, label_ids = get_message(message_id)
        subj = headers.get("Subject", "(no subject)")
        frm = headers.get("From", "(unknown)")
        
        # Triage using LLM
        t = triage_email(lambda p: llm_client.call(user_id, p), frm, subj, snippet)
        
        # Be conservative: only auto-spam when confident
        if t["label"] == "spam" and float(t.get("confidence", 0)) >= 0.85:
            spam_ids.append(message_id)
            if len(examples) < 5:
                examples.append(f"- {subj} / {frm}")
    
    if not spam_ids:
        await update.message.reply_text("No high-confidence spam found in unread Inbox.")
        return
    
    PENDING_SPAM[user_id] = spam_ids
    
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(f"Confirm: move {len(spam_ids)} to Spam", callback_data="spamconfirm:yes"),
        InlineKeyboardButton("Cancel", callback_data="spamconfirm:no"),
    ]])
    
    preview = "\n".join(examples)
    await update.message.reply_text(
        f"Found {len(spam_ids)} high-confidence spam messages.\nExamples:\n{preview}\n\nProceed?",
        reply_markup=kb
    )


async def unread_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unread command - show triaged unread emails."""
    if not allowed(update):
        return
    
    user_id = update.effective_user.id
    llm_client: LLMClient = context.bot_data.get("llm_client")
    
    msgs = list_unread(max_results=20)
    if not msgs:
        await update.message.reply_text("No unread emails in Inbox.")
        return
    
    meaningful = []
    uncertain = []
    spam_count = 0
    
    for m in msgs:
        message_id = m["id"]
        headers, snippet, label_ids = get_message(message_id)
        subj = headers.get("Subject", "(no subject)")
        frm = headers.get("From", "(unknown)")
        
        # Triage using LLM
        t = triage_email(lambda p: llm_client.call(user_id, p), frm, subj, snippet)
        label = t["label"]
        
        item = (message_id, subj, frm, snippet, t)
        if label == "meaningful":
            meaningful.append(item)
        elif label == "uncertain":
            uncertain.append(item)
        else:
            spam_count += 1
    
    await update.message.reply_text(
        f"Triage: {len(meaningful)} meaningful, {len(uncertain)} uncertain, {spam_count} suppressed as spam."
    )
    
    def send_item(item):
        message_id, subj, frm, snippet, t = item
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("Draft reply", callback_data=f"draft:{message_id}"),
            InlineKeyboardButton("Mark read", callback_data=f"read:{message_id}")
        ]])
        txt = f"Subject: {subj}\nFrom: {frm}\n\n{snippet}\n\nTriage: {t['label']} ({t['confidence']})"
        return txt, kb
    
    # Show meaningful first
    for item in meaningful:
        txt, kb = send_item(item)
        await update.message.reply_text(txt, reply_markup=kb)
    
    # Optionally show uncertain too
    for item in uncertain:
        txt, kb = send_item(item)
        await update.message.reply_text(txt, reply_markup=kb)


async def unread_all_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unread_all command - show all unread without triage."""
    if not allowed(update):
        return
    
    msgs = list_unread(max_results=10)
    await update.message.reply_text(f"Unread (raw) in Inbox: {len(msgs)}")
    
    for m in msgs:
        headers, snippet, label_ids = get_message(m["id"])
        await update.message.reply_text(
            f"Subject: {headers.get('Subject')}\nFrom: {headers.get('From')}\n\n{snippet}"
        )


async def jarvis_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /jarvis command - chat with LLM."""
    if not allowed(update):
        return
    
    user_id = update.effective_user.id
    text = " ".join(context.args).strip()
    
    if not text:
        await update.message.reply_text("Usage: /jarvis <message>")
        return
    
    llm_client: LLMClient = context.bot_data.get("llm_client")
    reply = llm_client.call(user_id, text)
    await update.message.reply_text(reply)


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle regular text messages with intelligent intent detection."""
    if not allowed(update):
        return
    if not update.message or not update.message.text:
        return
    
    bot_username = (context.bot.username or "").strip()
    text = update.message.text.strip()
    
    if not should_respond_in_chat(update, text, bot_username):
        return
    
    # Prevent single digits being treated as meaningful input
    if text in {"1", "2", "3", "4"}:
        await update.message.reply_text("Используйте /unread и кнопки для управления email.")
        return
    
    # Clean up mentions
    if bot_username:
        text = text.replace(f"@{bot_username}", "").strip()
    
    if text.lower().startswith("/jarvis"):
        text = text[len("/jarvis"):].strip()
    
    llm_client: LLMClient = context.bot_data.get("llm_client")
    
    # Try intelligent intent detection first
    from src.agent.intent import detect_intent_and_execute
    
    try:
        tool_result, llm_response = await detect_intent_and_execute(
            user_message=text,
            llm_client=llm_client,
            user_id=update.effective_user.id,
            context=context
        )
        
        # If tool was executed, send the LLM response
        if llm_response:
            await update.message.reply_text(llm_response)
            return
    except Exception as e:
        print(f"⚠️ Intent detection failed: {e}")
        # Continue with normal chat if intent detection fails
    
    # Fallback to normal chat
    reply = llm_client.call(update.effective_user.id, text)
    await update.message.reply_text(reply)


def register_handlers(app: Application, llm_client: LLMClient):
    """Register all handlers with the application."""
    # Store LLM client in bot_data for access in handlers
    app.bot_data["llm_client"] = llm_client
    
    # Command handlers - General
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("jarvis", jarvis_cmd))
    
    # Command handlers - Email
    app.add_handler(CommandHandler("spam_sweep", spam_sweep_cmd))
    app.add_handler(CommandHandler("unread", unread_cmd))
    app.add_handler(CommandHandler("unread_all", unread_all_cmd))
    
    # Command handlers - News & Channels
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("channels", channels_cmd))
    app.add_handler(CommandHandler("search", search_cmd))
    app.add_handler(CommandHandler("news_search", news_search_cmd))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(on_callback))
    
    # Message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
