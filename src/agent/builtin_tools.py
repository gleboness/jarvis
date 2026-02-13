"""Built-in tools for the agent."""
import asyncio
from typing import Optional
from .tools import register_tool


@register_tool(
    name="check_email",
    description="Проверяет непрочитанные письма в Gmail и показывает важные",
    parameters=[]
)
async def check_email_tool():
    """Check unread emails."""
    from src.gmail import list_unread, get_message
    from src.gmail.triage import triage_email
    from src.llm import LLMClient
    
    # This will be called with proper context in the actual implementation
    msgs = list_unread(max_results=10)
    
    if not msgs:
        return "📭 Нет непрочитанных писем"
    
    result = f"📧 Найдено {len(msgs)} непрочитанных писем:\n\n"
    
    for i, m in enumerate(msgs[:5], 1):  # Show first 5
        headers, snippet, label_ids = get_message(m["id"])
        subj = headers.get("Subject", "(без темы)")
        frm = headers.get("From", "")
        
        result += f"{i}. От: {frm}\n"
        result += f"   Тема: {subj}\n"
        result += f"   {snippet[:100]}...\n\n"
    
    return result


@register_tool(
    name="get_news_digest",
    description="Получает дайджест новостей из отслеживаемых Telegram каналов",
    parameters=[
        {
            "name": "digest_type",
            "description": "Тип дайджеста: 'brief' (краткий) или 'full' (полный)",
            "required": False
        }
    ]
)
async def get_news_digest_tool(digest_type: str = "brief"):
    """Get news digest."""
    from src.tools import aggregate_news, create_digest
    from src.tools.news_aggregator import format_messages_for_llm
    from src.llm import LLMClient
    from src.bot.prompts import SYSTEM_PROMPT
    
    # Aggregate news
    news_data = await aggregate_news(hours_back=24)
    
    if news_data['total_messages'] == 0:
        return "📭 Нет новых сообщений за последние 24 часа"
    
    # Format for LLM
    news_content = format_messages_for_llm(news_data, max_messages=30, max_chars_per_message=200)
    
    # Create LLM client
    llm_client = LLMClient(system_prompt=SYSTEM_PROMPT)
    
    # Create digest
    digest = create_digest(
        news_content=news_content,
        digest_type=digest_type,
        llm_client=llm_client,
        is_scheduled=False
    )
    
    header = f"📰 {'Подробная' if digest_type == 'full' else 'Краткая'} сводка новостей\n"
    header += f"📊 Обработано сообщений: {news_data['total_messages']}\n\n"
    
    return header + digest


@register_tool(
    name="web_search",
    description="Ищет информацию в интернете через DuckDuckGo",
    parameters=[
        {
            "name": "query",
            "description": "Поисковой запрос",
            "required": True
        }
    ]
)
async def web_search_tool(query: str):
    """Search the web."""
    from src.tools.web_search import search_web
    
    results = search_web(query, max_results=5, region="ru-ru")
    
    if not results:
        return f"🤷 Ничего не найдено по запросу: {query}"
    
    output = f"🔍 Результаты поиска: {query}\n\n"
    
    for i, result in enumerate(results, 1):
        title = result['title'][:100]
        body = result['body'][:200] if result['body'] else "Нет описания"
        
        output += f"{i}. {title}\n"
        output += f"   {body}...\n"
        output += f"   🔗 {result['url']}\n\n"
    
    return output


@register_tool(
    name="search_news",
    description="Ищет актуальные новости по конкретной теме",
    parameters=[
        {
            "name": "topic",
            "description": "Тема для поиска новостей",
            "required": True
        }
    ]
)
async def search_news_tool(topic: str):
    """Search news by topic."""
    from src.tools.web_search import search_news
    
    results = search_news(topic, max_results=5, region="ru-ru")
    
    if not results:
        return f"🤷 Новостей не найдено по теме: {topic}"
    
    output = f"📰 Новости по теме: {topic}\n\n"
    
    for i, result in enumerate(results, 1):
        title = result['title'][:100]
        source = result.get('source', 'N/A')
        date = result.get('date', '')
        
        output += f"{i}. {title}\n"
        output += f"   📍 {source}"
        if date:
            output += f" | {date}"
        output += f"\n   🔗 {result['url']}\n\n"
    
    return output


@register_tool(
    name="list_channels",
    description="Показывает список отслеживаемых Telegram каналов для новостей",
    parameters=[]
)
async def list_channels_tool():
    """List monitored channels."""
    from src.telegram_client.channels import get_monitored_channels
    
    channels = get_monitored_channels()
    
    if not channels:
        return "📋 Нет отслеживаемых каналов"
    
    output = "📋 Отслеживаемые каналы:\n\n"
    for ch in channels:
        title = ch.channel_title or ch.channel_username
        output += f"• {title} (@{ch.channel_username})\n"
    
    output += f"\n📊 Всего: {len(channels)} каналов"
    
    return output


@register_tool(
    name="add_channel",
    description="Добавляет новый Telegram канал в список отслеживаемых для новостей",
    parameters=[
        {
            "name": "channel_username",
            "description": "Username канала (с @ или без), например: bbcrussian или @bbcrussian",
            "required": True
        }
    ]
)
async def add_channel_tool(channel_username: str):
    """Add a channel to monitoring."""
    from src.telegram_client.channels import add_channel
    
    # Remove @ if present for consistency
    if channel_username.startswith('@'):
        channel_username = channel_username[1:]
    
    try:
        channel = await add_channel(channel_username)
        title = channel.channel_title or channel.channel_username
        return f"✅ Канал добавлен: {title} (@{channel.channel_username})"
    except Exception as e:
        return f"❌ Ошибка при добавлении канала @{channel_username}: {str(e)}"


@register_tool(
    name="remove_channel",
    description="Удаляет Telegram канал из списка отслеживаемых",
    parameters=[
        {
            "name": "channel_username",
            "description": "Username канала для удаления (с @ или без)",
            "required": True
        }
    ]
)
async def remove_channel_tool(channel_username: str):
    """Remove a channel from monitoring."""
    from src.telegram_client.channels import remove_channel
    
    # Remove @ if present
    if channel_username.startswith('@'):
        channel_username = channel_username[1:]
    
    success = remove_channel(channel_username)
    
    if success:
        return f"✅ Канал @{channel_username} удален из отслеживаемых"
    else:
        return f"❌ Канал @{channel_username} не найден в списке"


@register_tool(
    name="clear_all_channels",
    description="Удаляет ВСЕ каналы из списка отслеживаемых (очистка списка)",
    parameters=[]
)
async def clear_all_channels_tool():
    """Clear all monitored channels."""
    from src.telegram_client.channels import get_monitored_channels
    from src.database import SessionLocal, MonitoredChannel
    
    channels = get_monitored_channels()
    
    if not channels:
        return "📋 Список каналов уже пуст"
    
    count = len(channels)
    
    # Deactivate all channels
    db = SessionLocal()
    try:
        db.query(MonitoredChannel).update({"is_active": False})
        db.commit()
    finally:
        db.close()
    
    return f"🗑️ Очищен список каналов. Удалено: {count} каналов"


# Import all tools to register them
def init_builtin_tools():
    """Initialize all built-in tools."""
    # Tools are registered on import via decorators
    pass
