"""Create news digests using LLM."""
from typing import Literal
from datetime import datetime, timezone

from src.llm import LLMClient
from src.database import SessionLocal, NewsDigest


BRIEF_DIGEST_PROMPT = """Ты - ассистент новостей. Создай КРАТКУЮ сводку новостей.

Требования:
- Максимум 10-15 пунктов
- Каждый пункт - одно предложение
- Только самое важное и интересное
- Группируй похожие новости
- Используй эмодзи для категорий (📰🔥💰🚀🌍)

Формат:
📰 [Категория]
• Краткая новость 1
• Краткая новость 2

Новости:
{news_content}

Краткая сводка:"""


FULL_DIGEST_PROMPT = """Ты - ассистент новостей. Создай ПОДРОБНУЮ сводку новостей.

Требования:
- Сгруппируй новости по темам/категориям
- Для каждой темы - развернутое описание (2-3 предложения)
- Укажи источники и контекст
- Добавь краткий анализ или выводы
- Используй эмодзи для категорий
- Структурируй читаемо

Формат:
## 📰 Категория 1

**Основное событие:** описание
Источники: канал1, канал2
Контекст: дополнительная информация

## 🔥 Категория 2
...

Новости:
{news_content}

Подробная сводка:"""


def create_digest(
    news_content: str,
    digest_type: Literal['brief', 'full'],
    llm_client: LLMClient,
    is_scheduled: bool = False
) -> str:
    """
    Create a news digest using LLM.
    
    Args:
        news_content: Formatted news content
        digest_type: 'brief' for краткая or 'full' for полная
        llm_client: LLM client instance
        is_scheduled: Whether this is a scheduled digest
        
    Returns:
        Generated digest text
    """
    # Select appropriate prompt
    prompt_template = FULL_DIGEST_PROMPT if digest_type == 'full' else BRIEF_DIGEST_PROMPT
    prompt = prompt_template.format(news_content=news_content)
    
    # Generate digest (without history for cleaner output)
    digest = llm_client.call_without_history(prompt, temperature=0.3)
    
    # Save to database
    db = SessionLocal()
    try:
        # Count messages (rough estimate)
        message_count = news_content.count('[')  # Each message starts with [date]
        
        news_digest = NewsDigest(
            digest_type=digest_type,
            is_scheduled=is_scheduled,
            content=digest,
            message_count=message_count,
            created_at=datetime.now(timezone.utc)
        )
        db.add(news_digest)
        db.commit()
    finally:
        db.close()
    
    return digest
