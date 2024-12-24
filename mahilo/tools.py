from typing import Callable
from .registry import GlobalRegistry

def get_chat_with_agent_tool() -> Callable:
    """Get the chat_with_agent tool that can be bound to LLMs."""

    def chat_with_agent(agent_name: str, question: str) -> str:
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
            
        # add the question to the agent's queue
        agent.add_message_to_queue(question, "")
        
        return (
            f"I have put the question '{question}' in the queue for the agent named {agent_name}. "
            "You will hear back soon."
        )
    
    return chat_with_agent
