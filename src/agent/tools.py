"""Available tools for the agent."""
from typing import Dict, Any, List, Callable
import asyncio


# Tool registry
TOOLS: Dict[str, Dict[str, Any]] = {}


def register_tool(name: str, description: str, parameters: List[Dict[str, str]]):
    """Decorator to register a tool."""
    def decorator(func: Callable):
        TOOLS[name] = {
            "function": func,
            "description": description,
            "parameters": parameters,
        }
        return func
    return decorator


def get_available_tools() -> List[Dict[str, Any]]:
    """Get list of available tools for LLM."""
    tools_list = []
    for name, tool_data in TOOLS.items():
        tools_list.append({
            "name": name,
            "description": tool_data["description"],
            "parameters": tool_data["parameters"],
        })
    return tools_list


async def execute_tool(tool_name: str, parameters: Dict[str, Any]) -> str:
    """Execute a tool with given parameters."""
    if tool_name not in TOOLS:
        return f"Ошибка: инструмент '{tool_name}' не найден"
    
    tool = TOOLS[tool_name]
    func = tool["function"]
    
    try:
        # Check if function is async
        if asyncio.iscoroutinefunction(func):
            result = await func(**parameters)
        else:
            result = func(**parameters)
        return result
    except Exception as e:
        return f"Ошибка выполнения {tool_name}: {str(e)}"


def get_tools_description_for_llm() -> str:
    """Get formatted tools description for LLM prompt."""
    tools = get_available_tools()
    
    description = "Доступные инструменты:\n\n"
    for tool in tools:
        description += f"**{tool['name']}**\n"
        description += f"Описание: {tool['description']}\n"
        description += "Параметры:\n"
        for param in tool['parameters']:
            required = "(обязательно)" if param.get('required', False) else "(опционально)"
            description += f"  - {param['name']} {required}: {param['description']}\n"
        description += "\n"
    
    return description
