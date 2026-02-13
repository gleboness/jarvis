"""Handlers for news and channels commands."""
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.config import ALLOWED_USER_IDS
from src.telegram_client.channels import (
    get_monitored_channels,
    add_channel,
    remove_channel,
)
from src.tools import aggregate_news, search_web, search_news
from src.tools.news_aggregator import format_messages_for_llm
from src.tools.summarizer import create_digest
from src.llm import LLMClient


def allowed(update: Update) -> bool:
    """Check if user is allowed."""
    user = update.effective_user
    return user and user.id in ALLOWED_USER_IDS


async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /news command - generate news digest.
    Usage: /news [краткая|полная]
    """
    if not allowed(update):
        return
    
    # Parse arguments
    args = context.args
    digest_type = 'brief'  # Default
    
    if args:
        if 'полн' in args[0].lower() or 'full' in args[0].lower():
            digest_type = 'full'
        elif 'крат' in args[0].lower() or 'brief' in args[0].lower():
            digest_type = 'brief'
    
    await update.message.reply_text(
        f"🔄 Собираю новости и создаю {'подробную' if digest_type == 'full' else 'краткую'} сводку..."
    )
    
    try:
        llm_client: LLMClient = context.bot_data.get("llm_client")
        
        if not llm_client:
            await update.message.reply_text("❌ LLM клиент не инициализирован")
            return
        
        # Aggregate news from last 24 hours
        news_data = await aggregate_news(hours_back=24)
        
        if news_data['total_messages'] == 0:
            await update.message.reply_text("📭 Нет новых сообщений за последние 24 часа.")
            return
        
        # Format for LLM (limit to 50 messages to avoid token limits)
        news_content = format_messages_for_llm(news_data, max_messages=50, max_chars_per_message=300)
        
        # Check content length
        if len(news_content) > 15000:
            await update.message.reply_text("⚠️ Слишком много новостей, уменьшаю выборку...")
            news_content = format_messages_for_llm(news_data, max_messages=30, max_chars_per_message=200)
        
        # Create digest
        digest = create_digest(
            news_content=news_content,
            digest_type=digest_type,
            llm_client=llm_client,
            is_scheduled=False
        )
        
        # Send digest
        header = f"📰 {'Подробная' if digest_type == 'full' else 'Краткая'} сводка новостей\n"
        header += f"📊 Обработано сообщений: {news_data['total_messages']}\n\n"
        
        await update.message.reply_text(header + digest)
    
    except Exception as e:
        error_msg = f"❌ Ошибка при создании дайджеста: {str(e)[:200]}"
        if "LM Studio" in str(e) or "400" in str(e):
            error_msg += "\n\n💡 Проверьте:\n"
            error_msg += "1. Запущен ли LM Studio\n"
            error_msg += "2. Загружена ли модель\n"
            error_msg += "3. Работает ли сервер на порту 1234"
        await update.message.reply_text(error_msg)


async def channels_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /channels command - manage monitored channels.
    Usage: /channels [list|add @channel|remove @channel]
    """
    if not allowed(update):
        return
    
    args = context.args
    
    # No arguments - show list
    if not args:
        channels = get_monitored_channels()
        if not channels:
            await update.message.reply_text(
                "📋 Нет отслеживаемых каналов.\n\n"
                "Используйте: /channels add @channelname"
            )
            return
        
        text = "📋 Отслеживаемые каналы:\n\n"
        for ch in channels:
            title = ch.channel_title or ch.channel_username
            text += f"• {title} (@{ch.channel_username})\n"
        
        text += f"\n📊 Всего: {len(channels)} каналов"
        await update.message.reply_text(text)
        return
    
    # Add channel
    if args[0].lower() in ('add', 'добавить'):
        if len(args) < 2:
            await update.message.reply_text("Использование: /channels add @channelname")
            return
        
        channel_username = args[1].strip()
        try:
            channel = await add_channel(channel_username)
            await update.message.reply_text(
                f"✅ Канал добавлен: {channel.channel_title or channel.channel_username}"
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при добавлении канала: {e}")
        return
    
    # Remove channel
    if args[0].lower() in ('remove', 'delete', 'удалить'):
        if len(args) < 2:
            await update.message.reply_text("Использование: /channels remove @channelname")
            return
        
        channel_username = args[1].strip()
        success = remove_channel(channel_username)
        if success:
            await update.message.reply_text(f"✅ Канал удален: {channel_username}")
        else:
            await update.message.reply_text(f"❌ Канал не найден: {channel_username}")
        return
    
    await update.message.reply_text(
        "Использование:\n"
        "/channels - список каналов\n"
        "/channels add @channel - добавить канал\n"
        "/channels remove @channel - удалить канал"
    )


async def search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /search command - web search.
    Usage: /search <query>
    """
    if not allowed(update):
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /search <запрос>")
        return
    
    query = " ".join(args)
    await update.message.reply_text(f"🔍 Ищу: {query}...")
    
    try:
        # Try search with Russian region first
        results = search_web(query, max_results=5, region="ru-ru")
        
        if not results:
            await update.message.reply_text("🤷 Ничего не найдено. Попробуйте другой запрос.")
            return
        
        # Format results without markdown to avoid issues
        text = f"🔍 Результаты поиска: {query}\n\n"
        for i, result in enumerate(results, 1):
            title = result['title'][:100]  # Limit title length
            body = result['body'][:200] if result['body'] else "Нет описания"
            url = result['url']
            
            text += f"{i}. {title}\n"
            text += f"{body}...\n"
            text += f"🔗 {url}\n\n"
        
        # Limit total length for Telegram
        if len(text) > 3000:
            text = text[:3000] + "\n\n... (результаты обрезаны)"
        
        # Send results first
        await update.message.reply_text(text)
        
        # Then create summary with LLM
        llm_client: LLMClient = context.bot_data.get("llm_client")
        if llm_client:
            try:
                # Create a cleaner prompt for LLM
                results_text = ""
                for i, result in enumerate(results, 1):
                    results_text += f"{i}. {result['title']}\n{result['body'][:300]}\n\n"
                
                summary_prompt = (
                    f"Пользователь искал: '{query}'\n\n"
                    f"Результаты поиска:\n{results_text}\n\n"
                    f"Кратко ответь на вопрос пользователя на основе этих результатов (2-3 предложения):"
                )
                
                await update.message.reply_text("💭 Создаю краткое резюме...")
                summary = llm_client.call_without_history(summary_prompt, temperature=0.3)
                await update.message.reply_text(f"📝 Краткое резюме:\n\n{summary}")
            except Exception as llm_error:
                print(f"LLM summary error: {llm_error}")
                # Continue without summary if LLM fails
    
    except Exception as e:
        error_msg = f"❌ Ошибка поиска: {str(e)[:100]}"
        await update.message.reply_text(error_msg)


async def news_search_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle /news_search command - search for news on specific topic.
    Usage: /news_search <topic>
    """
    if not allowed(update):
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /news_search <тема>")
        return
    
    query = " ".join(args)
    await update.message.reply_text(f"📰 Ищу новости: {query}...")
    
    try:
        results = search_news(query, max_results=10, region="ru-ru")
        
        if not results:
            await update.message.reply_text("🤷 Новостей не найдено. Попробуйте другую тему.")
            return
        
        # Format news list
        news_list = f"📰 Найдено новостей: {len(results)}\n\n"
        for i, result in enumerate(results[:5], 1):  # Show first 5
            title = result['title'][:100]
            body = result['body'][:150] if result['body'] else ""
            source = result.get('source', 'N/A')
            date = result.get('date', '')
            
            news_list += f"{i}. {title}\n"
            if body:
                news_list += f"   {body}...\n"
            news_list += f"   📍 {source}"
            if date:
                news_list += f" | {date}"
            news_list += f"\n   🔗 {result['url']}\n\n"
        
        # Send news list
        await update.message.reply_text(news_list)
        
        # Create summary with LLM
        llm_client: LLMClient = context.bot_data.get("llm_client")
        if llm_client:
            try:
                # Format for LLM
                news_text = f"Новости по теме '{query}':\n\n"
                for i, result in enumerate(results, 1):
                    news_text += f"{i}. {result['title']}\n"
                    news_text += f"   {result['body'][:200]}\n"
                    news_text += f"   {result.get('source', '')} | {result.get('date', '')}\n\n"
                
                summary_prompt = (
                    f"Создай краткую сводку новостей по теме '{query}'.\n"
                    f"Выдели главное, упомяни ключевые события.\n"
                    f"3-5 пунктов максимум.\n\n{news_text}"
                )
                
                await update.message.reply_text("💭 Создаю сводку...")
                summary = llm_client.call_without_history(summary_prompt, temperature=0.3)
                await update.message.reply_text(f"📝 Краткая сводка:\n\n{summary}")
            except Exception as llm_error:
                print(f"LLM summary error: {llm_error}")
                # Continue without summary
    
    except Exception as e:
        error_msg = f"❌ Ошибка поиска новостей: {str(e)[:100]}"
        await update.message.reply_text(error_msg)
