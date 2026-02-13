"""Aggregate news from Telegram channels."""
from typing import List, Dict
from datetime import datetime
import asyncio

from src.telegram_client.channels import get_all_monitored_messages


async def aggregate_news(hours_back: int = 24) -> Dict[str, any]:
    """
    Aggregate news from all monitored Telegram channels.
    
    Args:
        hours_back: How many hours back to fetch messages
        
    Returns:
        Dict with aggregated news from all channels
    """
    messages_by_channel = await get_all_monitored_messages(hours_back)
    
    # Count total messages
    total_messages = sum(len(data['messages']) for data in messages_by_channel.values())
    
    return {
        'channels': messages_by_channel,
        'total_messages': total_messages,
        'time_range_hours': hours_back,
        'collected_at': datetime.now().isoformat(),
    }


def format_messages_for_llm(news_data: Dict, max_messages: int = 50, max_chars_per_message: int = 300) -> str:
    """
    Format aggregated news for LLM processing.
    
    Args:
        news_data: Output from aggregate_news()
        max_messages: Maximum number of messages to include (to avoid token limits)
        max_chars_per_message: Maximum characters per message
        
    Returns:
        Formatted string ready for LLM
    """
    if news_data['total_messages'] == 0:
        return "Нет новых сообщений за указанный период."
    
    output = []
    output.append(f"Собрано {news_data['total_messages']} сообщений за последние {news_data['time_range_hours']} часов:\n")
    
    message_count = 0
    
    for channel_username, data in news_data['channels'].items():
        if not data['messages'] or message_count >= max_messages:
            continue
        
        output.append(f"\n### {data['title']}")
        output.append(f"Сообщений: {len(data['messages'])}\n")
        
        for msg in data['messages']:
            if message_count >= max_messages:
                output.append(f"\n... (показаны первые {max_messages} сообщений из {news_data['total_messages']})")
                break
            
            # Format date
            date_str = msg['date'].strftime('%d.%m %H:%M')
            # Limit text length to avoid token limits
            text = msg['text'][:max_chars_per_message]
            if len(msg['text']) > max_chars_per_message:
                text += "..."
            output.append(f"[{date_str}] {text}")
            output.append("")  # Empty line
            message_count += 1
    
    return "\n".join(output)
