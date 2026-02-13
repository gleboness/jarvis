"""Intelligent agent with function calling."""
from .tools import get_available_tools, execute_tool
from .intent import detect_intent_and_execute

__all__ = [
    "get_available_tools",
    "execute_tool",
    "detect_intent_and_execute",
]
