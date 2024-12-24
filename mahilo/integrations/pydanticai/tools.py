from typing import Any, Callable
from pydantic_ai import Agent, RunContext

from mahilo.tools import get_chat_with_agent_tool

def get_chat_with_agent_tool_pydanticai(agent: Agent) -> Callable:
    """Get the chat with agent tool for PydanticAI."""
    return agent.tool(chat_with_agent_tool_pydanticai)

def chat_with_agent_tool_pydanticai(ctx: RunContext[Any], agent_name: str, your_name: str, question: str) -> str:
    """Chat with an agent by their name.
    
    This is a tool that can be used in a PydanticAI agent to chat with another agent.
    
    Args:
        ctx: The context of the PydanticAI agent.
        agent_name: The name of the agent to chat with.
        your_name: The name of the PydanticAI agent.
        question: The question/message to ask the agent.
    """
    tool = get_chat_with_agent_tool()
    return tool(agent_name, your_name, question)