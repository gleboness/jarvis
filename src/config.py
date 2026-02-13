"""Configuration and environment variables."""
import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
ALLOWED_USER_IDS = {int(x.strip()) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()}
GROUP_MODE = os.getenv("GROUP_MODE", "mentions").lower()  # off/mentions/commands

# Telegram Client (для чтения каналов)
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID")  # Получить на my.telegram.org
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH")
TELEGRAM_SESSION_NAME = os.getenv("TELEGRAM_SESSION_NAME", "jarvis_client")

# LM Studio
LM_BASE = os.getenv("LM_BASE", "http://127.0.0.1:1234/v1")
LM_MODEL = os.getenv("LM_MODEL", "llama-3.1-8b-instruct")

# Gmail
GMAIL_TOKEN_FILE = os.getenv("GMAIL_TOKEN_FILE", "gmail_token.json")
GMAIL_CREDS_FILE = os.getenv("GMAIL_CREDS_FILE", "credentials.json")
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
]

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///jarvis.db")

# News Settings
NEWS_SCHEDULE_MORNING = os.getenv("NEWS_SCHEDULE_MORNING", "10:00")  # Время утренней сводки
NEWS_SCHEDULE_EVENING = os.getenv("NEWS_SCHEDULE_EVENING", "21:00")  # Время вечерней сводки
NEWS_TIMEZONE = os.getenv("NEWS_TIMEZONE", "Europe/Moscow")

# Channels to monitor (можно задать в .env через запятую или в БД)
DEFAULT_NEWS_CHANNELS = os.getenv("DEFAULT_NEWS_CHANNELS", "").split(",") if os.getenv("DEFAULT_NEWS_CHANNELS") else []
