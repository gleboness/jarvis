"""Tools for LLM - web search, news aggregation, summarization."""
from .web_search import search_web, search_news
from .news_aggregator import aggregate_news
from .summarizer import create_digest

__all__ = [
    "search_web",
    "search_news",
    "aggregate_news",
    "create_digest",
]
