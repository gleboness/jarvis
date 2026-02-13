"""LM Studio client."""
import requests
from collections import defaultdict, deque
from typing import Dict, List

from src.config import LM_BASE, LM_MODEL


class LLMClient:
    """Client for interacting with LM Studio."""
    
    def __init__(self, system_prompt: str = "You are Jarvis, a helpful assistant. Be concise."):
        self.base_url = LM_BASE
        self.model = LM_MODEL
        self.system_prompt = system_prompt
        # Per-user chat memory (last 20 turns per user)
        self.history: Dict[int, deque] = defaultdict(lambda: deque(maxlen=20))
    
    def call(self, user_id: int, user_text: str, temperature: float = 0.4) -> str:
        """
        Call LM Studio with user text and conversation history.
        
        Args:
            user_id: Telegram user ID for conversation context
            user_text: User's message
            temperature: LLM temperature (default 0.4)
            
        Returns:
            LLM response text
        """
        url = f"{self.base_url}/chat/completions"
        
        messages = [{"role": "system", "content": self.system_prompt}]
        messages.extend(list(self.history[user_id]))
        messages.append({"role": "user", "content": user_text})
        
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        r = requests.post(url, json=payload, timeout=120)
        r.raise_for_status()
        content = r.json()["choices"][0]["message"]["content"]
        
        # Update history
        self.history[user_id].append({"role": "user", "content": user_text})
        self.history[user_id].append({"role": "assistant", "content": content})
        
        return content
    
    def call_without_history(self, prompt: str, temperature: float = 0.4) -> str:
        """
        Call LM Studio without conversation history (for one-off tasks like email drafting).
        
        Args:
            prompt: Complete prompt to send
            temperature: LLM temperature (default 0.4)
            
        Returns:
            LLM response text
        """
        url = f"{self.base_url}/chat/completions"
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        payload = {"model": self.model, "messages": messages, "temperature": temperature}
        
        try:
            r = requests.post(url, json=payload, timeout=120)
            r.raise_for_status()
            content = r.json()["choices"][0]["message"]["content"]
            return content
        except requests.exceptions.HTTPError as e:
            # Log the error with more details
            error_msg = f"LM Studio error: {e}"
            if hasattr(e.response, 'text'):
                error_msg += f"\nResponse: {e.response.text[:500]}"
            print(error_msg)
            raise Exception(f"LLM request failed: {str(e)}") from e
        except Exception as e:
            print(f"Unexpected error calling LLM: {e}")
            raise
