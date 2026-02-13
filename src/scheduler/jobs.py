"""APScheduler jobs for automated news digests."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import asyncio
from datetime import datetime
import pytz

from src.config import (
    NEWS_SCHEDULE_MORNING,
    NEWS_SCHEDULE_EVENING,
    NEWS_TIMEZONE,
    ALLOWED_USER_IDS
)
from src.tools import aggregate_news, create_digest
from src.tools.news_aggregator import format_messages_for_llm


# Global scheduler instance
_scheduler = None
_bot_application = None
_llm_client = None


async def send_scheduled_digest(digest_type: str = 'full'):
    """
    Generate and send scheduled news digest to all allowed users.
    
    Args:
        digest_type: 'brief' or 'full'
    """
    if not _bot_application or not _llm_client:
        print("Bot or LLM client not initialized")
        return
    
    try:
        # Calculate time range (12 hours for morning/evening digests)
        hours_back = 12
        
        # Aggregate news from channels
        news_data = await aggregate_news(hours_back=hours_back)
        
        if news_data['total_messages'] == 0:
            print(f"No news to digest at {datetime.now()}")
            return
        
        # Format for LLM
        news_content = format_messages_for_llm(news_data)
        
        # Create digest
        digest = create_digest(
            news_content=news_content,
            digest_type='full',  # Always full for scheduled
            llm_client=_llm_client,
            is_scheduled=True
        )
        
        # Get current time for header
        now = datetime.now()
        time_emoji = "🌅" if now.hour < 12 else "🌆"
        header = f"{time_emoji} Новостная сводка за последние {hours_back} часов\n"
        header += f"📊 Обработано сообщений: {news_data['total_messages']}\n\n"
        
        full_message = header + digest
        
        # Send to all allowed users
        for user_id in ALLOWED_USER_IDS:
            try:
                await _bot_application.bot.send_message(
                    chat_id=user_id,
                    text=full_message,
                    parse_mode=None  # Plain text for better compatibility
                )
                print(f"Sent scheduled digest to user {user_id}")
            except Exception as e:
                print(f"Failed to send digest to user {user_id}: {e}")
    
    except Exception as e:
        print(f"Error in scheduled digest: {e}")


def start_scheduler(bot_application, llm_client):
    """
    Start the scheduler for automated news digests.
    
    Args:
        bot_application: Telegram Application instance
        llm_client: LLM client instance
    """
    global _scheduler, _bot_application, _llm_client
    
    _bot_application = bot_application
    _llm_client = llm_client
    
    if _scheduler is not None:
        print("Scheduler already running")
        return
    
    _scheduler = AsyncIOScheduler(timezone=NEWS_TIMEZONE)
    
    # Parse time strings (format: "HH:MM")
    morning_hour, morning_minute = map(int, NEWS_SCHEDULE_MORNING.split(':'))
    evening_hour, evening_minute = map(int, NEWS_SCHEDULE_EVENING.split(':'))
    
    # Morning digest
    _scheduler.add_job(
        send_scheduled_digest,
        trigger=CronTrigger(
            hour=morning_hour,
            minute=morning_minute,
            timezone=NEWS_TIMEZONE
        ),
        id='morning_digest',
        name='Morning News Digest',
        replace_existing=True,
        kwargs={'digest_type': 'full'}
    )
    
    # Evening digest
    _scheduler.add_job(
        send_scheduled_digest,
        trigger=CronTrigger(
            hour=evening_hour,
            minute=evening_minute,
            timezone=NEWS_TIMEZONE
        ),
        id='evening_digest',
        name='Evening News Digest',
        replace_existing=True,
        kwargs={'digest_type': 'full'}
    )
    
    _scheduler.start()
    print(f"📅 Scheduler started:")
    print(f"  🌅 Morning digest: {NEWS_SCHEDULE_MORNING} {NEWS_TIMEZONE}")
    print(f"  🌆 Evening digest: {NEWS_SCHEDULE_EVENING} {NEWS_TIMEZONE}")


def stop_scheduler():
    """Stop the scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        print("Scheduler stopped")
