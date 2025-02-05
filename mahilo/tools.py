from typing import Callable
from .registry import GlobalRegistry
from .message_protocol import MessageType

def get_chat_with_agent_tool() -> Callable:
    """Get the chat_with_agent tool that can be bound to LLMs."""

    def chat_with_agent(agent_name: str, your_name: str, question: str) -> str:
        """Chat with an agent by their name."""
        registry = GlobalRegistry.get_agent_registry()
        if not registry:
            return "Error: Agent registry not initialized"
            
        agent = registry.get_agent(agent_name)
        if not agent:
            return f"Error: Agent '{agent_name}' not found"
            
        # if agent is not active, activate it
        if not agent.is_active():
            agent.activate()
            
        # Send message through broker instead of directly to queue
        registry.send_message_to_agent(
            sender=your_name,
            recipient=agent_name,
            message=question,
            message_type=MessageType.DIRECT
        )
        
        return (
            f"I have sent the message '{question}' to the agent named {agent_name}. "
            "You will hear back soon."
        )
    
    return chat_with_agent
