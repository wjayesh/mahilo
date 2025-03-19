from typing import Callable, Dict, Any, Optional
from .registry import GlobalRegistry
from .message_protocol import MessageType

def get_chat_with_agent_tool() -> Callable:
    """Get a tool for chatting with another agent."""
    
    async def chat_with_agent(agent_name: str, your_name: str, question: str) -> str:
        """Chat with another agent.
        
        Args:
            agent_name: Name of the agent to chat with
            your_name: Your agent's name
            question: The message to send
            
        Returns:
            A confirmation message
        """
        registry = GlobalRegistry.get_agent_registry()
        agent = registry.get_agent(agent_name)
        
        if not agent:
            return f"Error: Agent '{agent_name}' not found"
            
        # if agent is not active, activate it
        if not agent.is_active():
            agent.activate()
            
        # Send message through broker instead of directly to queue
        await registry.send_message_to_agent(
            sender=your_name,
            recipient=agent_name,
            message=question,
            message_type=MessageType.DIRECT
        )
        
        return (
            f"Message sent to {agent_name}. "
            f"They will process it and respond when ready."
        )
    
    return chat_with_agent
