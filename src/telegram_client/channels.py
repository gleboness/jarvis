"""Channel management and message retrieval."""
from typing import List
from datetime import datetime, timezone
import asyncio

from src.database import SessionLocal, MonitoredChannel
from .client import get_telegram_client


def get_monitored_channels() -> List[MonitoredChannel]:
    """Get list of active monitored channels from database."""
    db = SessionLocal()
    try:
        channels = db.query(MonitoredChannel).filter(
            MonitoredChannel.is_active == True
        ).all()
        return channels
    finally:
        db.close()


async def add_channel(channel_username: str) -> MonitoredChannel:
    """Add a channel to monitoring list."""
    db = SessionLocal()
    try:
        # Check if already exists
        existing = db.query(MonitoredChannel).filter(
            MonitoredChannel.channel_username == channel_username
        ).first()
        
        if existing:
            existing.is_active = True
            db.commit()
            return existing
        
        # Resolve channel info
        client = get_telegram_client()
        channel_info = await client.resolve_channel(channel_username)
        
        channel = MonitoredChannel(
            channel_username=channel_username,
            channel_title=channel_info['title'] if channel_info else None,
            is_active=True
        )
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel
    finally:
        db.close()


def remove_channel(channel_username: str) -> bool:
    """Remove a channel from monitoring (soft delete)."""
    db = SessionLocal()
    try:
        channel = db.query(MonitoredChannel).filter(
            MonitoredChannel.channel_username == channel_username
        ).first()
        
        if channel:
            channel.is_active = False
            db.commit()
            return True
        return False
    finally:
        db.close()


async def get_channel_messages(channel_username: str, hours_back: int = 24) -> List[dict]:
    """Get messages from a specific channel."""
    client = get_telegram_client()
    messages = await client.get_channel_messages(channel_username, hours_back=hours_back)
    
    # Update last_checked in database
    db = SessionLocal()
    try:
        channel = db.query(MonitoredChannel).filter(
            MonitoredChannel.channel_username == channel_username
        ).first()
        if channel:
            channel.last_checked = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()
    
    return messages


async def get_all_monitored_messages(hours_back: int = 24) -> dict:
    """Get messages from all monitored channels."""
    channels = get_monitored_channels()
    all_messages = {}
    
    for channel in channels:
        messages = await get_channel_messages(channel.channel_username, hours_back)
        all_messages[channel.channel_username] = {
            'title': channel.channel_title or channel.channel_username,
            'messages': messages
        }
    
    return all_messages
