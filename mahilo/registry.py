from typing import TYPE_CHECKING, Optional, Dict, Protocol
from threading import Lock

if TYPE_CHECKING:
    from mahilo.agent import BaseAgent

class AgentRegistry(Protocol):
    def get_agent(self, agent_name: str) -> Optional['BaseAgent']:
        ...
    def get_agent_types_with_description(self) -> Dict[str, str]:
        ...

class GlobalRegistry:
    _instance = None
    _lock = Lock()
    _agent_registry: Optional[AgentRegistry] = None

    @classmethod
    def _ensure_instance(cls):
        """Ensure instance exists under lock."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._agent_registry = None
        return cls._instance

    @classmethod
    def set_agent_registry(cls, registry: AgentRegistry) -> None:
        with cls._lock:
            instance = cls._ensure_instance()
            instance._agent_registry = registry

    @classmethod
    def get_agent_registry(cls) -> Optional[AgentRegistry]:
        with cls._lock:
            instance = cls._ensure_instance()
            return instance._agent_registry