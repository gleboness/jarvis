"""Intent detection and execution."""
import json
import re
from typing import Dict, Any, Optional, Tuple
from src.llm import LLMClient
from .tools import get_tools_description_for_llm, execute_tool


INTENT_DETECTION_PROMPT = """Ты - умный ассистент Jarvis. Проанализируй сообщение пользователя и реши какой инструмент использовать.

{tools_description}

**Правила:**
1. Проанализируй намерение пользователя
2. Выбери ОДИН подходящий инструмент или "none" если инструменты не нужны
3. Извлеки нужные параметры из сообщения
4. Верни ТОЛЬКО валидный JSON без дополнительного текста

**Формат ответа:**
```json
{{
  "tool": "название_инструмента",
  "parameters": {{
    "param1": "value1",
    "param2": "value2"
  }},
  "reasoning": "почему выбран этот инструмент"
}}
```

Если инструменты не нужны (просто вопрос для беседы):
```json
{{
  "tool": "none",
  "parameters": {{}},
  "reasoning": "пользователь хочет просто поговорить"
}}
```

**Примеры:**

Пользователь: "какие у меня непрочитанные письма?"
```json
{{
  "tool": "check_email",
  "parameters": {{}},
  "reasoning": "пользователь спрашивает про почту"
}}
```

Пользователь: "покажи новости за сегодня"
```json
{{
  "tool": "get_news_digest",
  "parameters": {{"digest_type": "brief"}},
  "reasoning": "пользователь хочет новости"
}}
```

Пользователь: "найди информацию про llama 3.3"
```json
{{
  "tool": "web_search",
  "parameters": {{"query": "llama 3.3"}},
  "reasoning": "нужен поиск в интернете"
}}
```

Пользователь: "привет как дела?"
```json
{{
  "tool": "none",
  "parameters": {{}},
  "reasoning": "обычное приветствие"
}}
```

Пользователь: "добавь канал bbcrussian"
```json
{{
  "tool": "add_channel",
  "parameters": {{"channel_username": "bbcrussian"}},
  "reasoning": "пользователь хочет добавить канал"
}}
```

Пользователь: "удали канал @meduzalive"
```json
{{
  "tool": "remove_channel",
  "parameters": {{"channel_username": "@meduzalive"}},
  "reasoning": "пользователь хочет удалить канал"
}}
```

Пользователь: "очисти список каналов"
```json
{{
  "tool": "clear_all_channels",
  "parameters": {{}},
  "reasoning": "пользователь хочет очистить весь список"
}}
```

Сообщение пользователя: "{user_message}"

Твой ответ (только JSON):"""


async def detect_intent_and_execute(
    user_message: str,
    llm_client: LLMClient,
    user_id: int,
    context: Any = None
) -> Tuple[Optional[str], Optional[str]]:
    """
    Detect user intent and execute appropriate tool.
    
    Args:
        user_message: User's message
        llm_client: LLM client instance
        user_id: Telegram user ID
        context: Telegram context for accessing bot data
        
    Returns:
        Tuple of (tool_result, llm_response)
        - tool_result: Result from tool execution (if any)
        - llm_response: LLM response to user
    """
    # Get tools description
    tools_desc = get_tools_description_for_llm()
    
    # Create prompt
    prompt = INTENT_DETECTION_PROMPT.format(
        tools_description=tools_desc,
        user_message=user_message
    )
    
    # Get LLM decision
    try:
        llm_response = llm_client.call_without_history(prompt, temperature=0.2)
        
        # Extract JSON from response
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            # Try to find JSON without code blocks
            json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
            else:
                # Fallback: no tool needed
                return None, None
        
        # Parse JSON
        decision = json.loads(json_str)
        tool_name = decision.get("tool", "none")
        parameters = decision.get("parameters", {})
        reasoning = decision.get("reasoning", "")
        
        print(f"🤖 Intent detected: {tool_name}")
        print(f"📝 Reasoning: {reasoning}")
        print(f"⚙️ Parameters: {parameters}")
        
        # If no tool needed, return None to continue with normal chat
        if tool_name == "none" or not tool_name:
            return None, None
        
        # Execute tool
        tool_result = await execute_tool(tool_name, parameters)
        
        # Create response with tool result
        response_prompt = f"""Пользователь спросил: "{user_message}"

Я выполнил действие и получил результат:

{tool_result}

Ответь пользователю естественным образом, используя этот результат.
Будь кратким и полезным."""
        
        final_response = llm_client.call_without_history(response_prompt, temperature=0.4)
        
        return tool_result, final_response
        
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse LLM response as JSON: {e}")
        print(f"Response was: {llm_response[:200]}")
        return None, None
    except Exception as e:
        print(f"❌ Error in intent detection: {e}")
        return None, None
