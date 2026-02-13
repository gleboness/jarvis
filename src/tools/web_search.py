"""Web search using DuckDuckGo."""
from typing import List, Dict
from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 5, region: str = "ru-ru") -> List[Dict[str, str]]:
    """
    Search the web using DuckDuckGo.
    
    Args:
        query: Search query
        max_results: Maximum number of results to return
        region: Region for search (default: ru-ru for Russian results)
        
    Returns:
        List of dicts with keys: title, url, body (snippet)
    """
    try:
        with DDGS() as ddgs:
            results = []
            # Use region parameter for better localized results
            search_results = ddgs.text(
                query,
                region=region,
                safesearch='moderate',
                max_results=max_results
            )
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('href', ''),
                    'body': result.get('body', ''),
                })
            
            return results
    except Exception as e:
        print(f"Web search error: {e}")
        print(f"Query was: {query}")
        return []


def search_news(query: str, max_results: int = 5, region: str = "ru-ru") -> List[Dict[str, str]]:
    """
    Search news using DuckDuckGo News.
    
    Args:
        query: Search query
        max_results: Maximum number of results
        region: Region for search (default: ru-ru)
        
    Returns:
        List of news articles
    """
    try:
        with DDGS() as ddgs:
            results = []
            search_results = ddgs.news(
                query,
                region=region,
                safesearch='moderate',
                max_results=max_results
            )
            
            for result in search_results:
                results.append({
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'body': result.get('body', ''),
                    'date': result.get('date', ''),
                    'source': result.get('source', ''),
                })
            
            return results
    except Exception as e:
        print(f"News search error: {e}")
        print(f"Query was: {query}")
        return []
