from .client import Client
from .cli import cli

# Lazy imports for server components
def __getattr__(name):
    if name in ["BaseAgent", "AgentManager", "Session", "ServerManager"]:
        from .agent import BaseAgent
        from .agent_manager import AgentManager
        from .session import Session
        from .server import ServerManager
        
        # Add them to the module's namespace for subsequent imports
        globals().update({
            "BaseAgent": BaseAgent,
            "AgentManager": AgentManager,
            "Session": Session,
            "ServerManager": ServerManager
        })
        return globals()[name]
    raise AttributeError(f"module 'mahilo' has no attribute '{name}'")

__all__ = ["Client", "cli", "BaseAgent", "AgentManager", "Session", "ServerManager"]
