"""Database models."""
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone
from src.config import DATABASE_URL

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


class PendingEmailDraft(Base):
    """Stores email drafts pending user approval."""
    __tablename__ = "pending_email_drafts"
    
    id = Column(Integer, primary_key=True)
    telegram_user_id = Column(String, index=True)
    message_id = Column(String)
    draft_id = Column(String, unique=True)
    draft_text = Column(Text)


class MonitoredChannel(Base):
    """Telegram channels to monitor for news."""
    __tablename__ = "monitored_channels"
    
    id = Column(Integer, primary_key=True)
    channel_username = Column(String, unique=True, nullable=False)  # @channelname или ID
    channel_title = Column(String)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_checked = Column(DateTime, nullable=True)
    
    def __repr__(self):
        return f"<MonitoredChannel {self.channel_username}>"


class NewsDigest(Base):
    """Store news digests history."""
    __tablename__ = "news_digests"
    
    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    digest_type = Column(String)  # 'brief' или 'full'
    is_scheduled = Column(Boolean, default=False)  # Auto or manual
    content = Column(Text)
    message_count = Column(Integer, default=0)
    
    def __repr__(self):
        return f"<NewsDigest {self.created_at} ({self.digest_type})>"


def init_db():
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)
