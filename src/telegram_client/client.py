"""Telethon client for reading Telegram channels."""
from telethon import TelegramClient
from telethon.tl.types import Message
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import asyncio

from src.config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION_NAME


class TelegramClientManager:
    """Manages Telethon client for reading channels."""
    
    def __init__(self):
        if not TELEGRAM_API_ID or not TELEGRAM_API_HASH:
            raise ValueError(
                "TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env\n"
                "Get them from https://my.telegram.org/apps"
            )
        
        self.client = TelegramClient(
            TELEGRAM_SESSION_NAME,
            int(TELEGRAM_API_ID),
            TELEGRAM_API_HASH
        )
        self._connected = False
    
    async def connect(self):
        """Connect to Telegram."""
        if not self._connected:
            await self.client.start()
            self._connected = True
    
    async def disconnect(self):
        """Disconnect from Telegram."""
        if self._connected:
            await self.client.disconnect()
            self._connected = False
    
    async def get_channel_messages(
        self,
        channel_username: str,
        hours_back: int = 24,
        limit: int = 100
    ) -> List[dict]:
        """
        Get recent messages from a channel.
        
        Args:
            channel_username: Channel username (with or without @) or ID
            hours_back: How many hours back to fetch messages
            limit: Maximum number of messages to fetch
            
        Returns:
            List of message dicts with keys: id, date, text, sender
        """
        await self.connect()
        
        # Remove @ if present
        if channel_username.startswith('@'):
            channel_username = channel_username[1:]
        
        # Calculate time threshold (with UTC timezone)
        time_threshold = datetime.now(timezone.utc) - timedelta(hours=hours_back)
        
        messages = []
        try:
            async for message in self.client.iter_messages(
                channel_username,
                limit=limit,
                offset_date=datetime.now(timezone.utc)
            ):
                if message.date < time_threshold:
                    break
                
                if message.text:  # Only text messages
                    messages.append({
                        'id': message.id,
                        'date': message.date,
                        'text': message.text,
                        'sender': channel_username,
                        'views': getattr(message, 'views', 0),
                    })
        except Exception as e:
            print(f"Error fetching messages from {channel_username}: {e}")
        
        return messages
    
    async def resolve_channel(self, channel_username: str) -> Optional[dict]:
        """
        Get channel info.
        
        Args:
            channel_username: Channel username or ID
            
        Returns:
            Dict with channel info or None
        """
        await self.connect()
        
        try:
            entity = await self.client.get_entity(channel_username)
            return {
                'id': entity.id,
                'title': getattr(entity, 'title', ''),
                'username': getattr(entity, 'username', ''),
            }
        except Exception as e:
            print(f"Error resolving channel {channel_username}: {e}")
            return None


# Singleton instance
_telegram_client = None


def get_telegram_client() -> TelegramClientManager:
    """Get or create TelegramClientManager instance."""
    global _telegram_client
    if _telegram_client is None:
        _telegram_client = TelegramClientManager()
    return _telegram_client
