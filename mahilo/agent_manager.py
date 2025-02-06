from typing import Dict, List, Optional
from .agent import BaseAgent
from .registry import GlobalRegistry, AgentRegistry
from .message_protocol import MessageBroker, MessageEnvelope, MessageType
from .message_store import SQLiteMessageStore
from .monitoring import EventType, MahiloTelemetry


class AgentManager(AgentRegistry):
    """A class to manage agents of different types.
    
    This class implements the AgentRegistry protocol and provides additional functionality
    for managing agents and their communication.
    """
    def __init__(self, secret_key: str = None, db_path: str = "messages.db", 
                 service_name: str = "mahilo"):
        self.agents: Dict[str, BaseAgent] = {}
        self.store = SQLiteMessageStore(db_path)
        self.telemetry = MahiloTelemetry(service_name)
        self.message_broker = MessageBroker(
            secret_key=secret_key,
            store=self.store,
            telemetry=self.telemetry
        )
        # Register self with global registry
        GlobalRegistry.set_agent_registry(self)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the AgentManager."""
        if agent.name in self.agents:
            raise ValueError(f"Agent with name {agent.name} is already registered.")
        agent._agent_manager = self
        agent._telemetry = self.telemetry
        self.agents[agent.name] = agent
        
        self.telemetry.record_event(
            event_type=EventType.AGENT_ACTIVATED,
            agent_id=agent.name,
            details={
                "type": agent.TYPE,
                "can_contact": agent.can_contact
            }
        )

    def get_agent(self, agent_name: str) -> Optional[BaseAgent]:
        """Return the agent of the given name. Implements AgentRegistry protocol."""
        return self.agents.get(agent_name)
    
    def get_all_agent_types(self) -> List[str]:
        """Return a list of all registered agent types."""
        return list(self.agents.keys())

    def get_all_agents(self) -> List[BaseAgent]:
        """Return a list of all registered agents."""
        return list(self.agents.values())

    def is_agent_registered(self, agent_name: str) -> bool:
        """Check if an agent of the given name is registered."""
        return agent_name in self.agents

    def unregister_agent(self, agent_name: str) -> None:
        """Unregister the agent of the given name."""
        if agent_name in self.agents:
            self.telemetry.record_event(
                event_type=EventType.AGENT_DEACTIVATED,
                agent_id=agent_name
            )
            del self.agents[agent_name]

    def unregister_all_agents(self) -> None:
        """Unregister all agents."""
        for agent_name in list(self.agents.keys()):
            self.unregister_agent(agent_name)
        self.agents.clear()

    def get_agent_types_with_description(self) -> Dict[str, str]:
        """Return a list of all registered agent types with their descriptions."""
        return {agent.name: agent.short_description for agent in self.agents.values()}
    
    def send_message_to_agent(self, sender: str, recipient: str, 
                            message: str, message_type: MessageType = MessageType.DIRECT,
                            correlation_id: Optional[str] = None) -> None:
        """Send a message to an agent."""
        envelope = MessageEnvelope.create(
            sender=sender,
            recipient=recipient,
            payload=message,
            message_type=message_type,
            correlation_id=correlation_id,
            secret_key=self.message_broker.secret_key
        )
        self.message_broker.send_message(envelope)
    
    def get_agent_messages(self, agent_name: str, num_messages: int = 7) -> str:
        """Return messages from all agents' sessions except the current agent."""
        messages = []
        for agent in self.agents.values():
            if agent.name != agent_name and agent._session:
                agent_messages = agent._session.get_last_n_messages(num_messages)
                if agent_messages:  # Only add if there are messages
                    context = f"\nOther Conversations: {agent.name}\n"
                    context += "\n".join([
                        f"{message['role']}: {message['content']}" 
                        for message in agent_messages
                    ])
                    messages.append(context)
        
        return "\n".join(messages) if messages else ""
        
    def populate_can_contact_for_agents(self) -> None:
        """Populate the can_contact list for all agents."""
        # if the can_contact is empty, set it to all agent names
        for agent in self.agents.values():
            if not agent.can_contact:
                agent.can_contact = list(self.agents.keys())

    def cleanup_old_messages(self, max_age_days: int = 30) -> None:
        """Clean up old processed messages."""
        if self.store:
            self.store.cleanup_old_messages(max_age_days)
            
    def get_agent_metrics(self, agent_id: Optional[str] = None) -> Dict:
        """Get metrics for an agent or all agents."""
        if self.telemetry:
            return self.telemetry.get_metrics(agent_id)
        return {}