"""Main entry point for Jarvis Telegram bot."""
from telegram.ext import Application
from telegram import BotCommand

from src.config import BOT_TOKEN
from src.database import init_db
from src.llm import LLMClient
from src.bot import register_handlers
from src.bot.prompts import SYSTEM_PROMPT
from src.scheduler import start_scheduler, stop_scheduler
from src.agent.builtin_tools import init_builtin_tools


async def setup_commands(app: Application):
    """Setup bot commands menu."""
    commands = [
        BotCommand("start", "Запустить бота и показать приветствие"),
        BotCommand("jarvis", "Отправить сообщение AI ассистенту"),
        BotCommand("unread", "Показать непрочитанные письма с триажем"),
        BotCommand("unread_all", "Показать все непрочитанные письма"),
        BotCommand("spam_sweep", "Сканировать inbox на спам"),
        BotCommand("news", "Получить дайджест новостей"),
        BotCommand("channels", "Управление отслеживаемыми каналами"),
        BotCommand("search", "Поиск в интернете с AI обобщением"),
        BotCommand("news_search", "Поиск новостей по теме"),
    ]
    await app.bot.set_my_commands(commands)


def main():
    """Run the bot."""
    # Initialize database
    init_db()
    print("✅ Database initialized")
    
    # Initialize built-in tools for agent
    init_builtin_tools()
    print("✅ Agent tools initialized")
    
    # Initialize LLM client
    llm_client = LLMClient(system_prompt=SYSTEM_PROMPT)
    print("✅ LLM client initialized")
    
    # Create Telegram application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Register handlers
    register_handlers(app, llm_client)
    print("✅ Bot handlers registered")
    
    # Setup commands menu
    app.post_init = setup_commands
    print("✅ Bot commands menu configured")
    
    # Start scheduler for automated news digests
    try:
        start_scheduler(app, llm_client)
        print("✅ News scheduler started")
    except Exception as e:
        print(f"⚠️ Warning: Could not start scheduler: {e}")
        print("   (This is normal if Telegram client is not configured yet)")
    
    # Start polling
    print("\n🤖 Jarvis bot is online!")
    print("=" * 50)
    try:
        app.run_polling()
    except KeyboardInterrupt:
        print("\n\n🛑 Shutting down...")
        stop_scheduler()
        print("👋 Goodbye!")


if __name__ == "__main__":
    main()
