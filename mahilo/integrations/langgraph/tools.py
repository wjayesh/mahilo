from typing import Callable
from langchain_core.tools import tool
from mahilo.tools import get_chat_with_agent_tool

def get_chat_with_agent_tool_langgraph() -> Callable:
    """Get the chat_with_agent tool that can be bound to LLMs."""
    return tool(get_chat_with_agent_tool())