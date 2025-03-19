from typing import Dict, List, Optional, Callable
from .agent import BaseAgent
from .registry import GlobalRegistry, AgentRegistry
from .message_protocol import MessageBroker, MessageEnvelope, MessageType
from .message_store import SQLiteMessageStore
from .monitoring import EventType, MahiloTelemetry
from .policy import Policy, PolicyManager, MessageValidator, PolicyViolation, PolicyType, create_default_policies


class AgentManager(AgentRegistry):
    """A class to manage agents of different types.
    
    This class implements the AgentRegistry protocol and provides additional functionality
    for managing agents and their communication.
    """
    def __init__(self, secret_key: str = None, db_path: str = "messages.db", 
                 service_name: str = "mahilo", validator_model_name: Optional[str] = None):
        """Initialize an AgentManager.
        
        Args:
            secret_key: Optional secret key for message signing
            db_path: Path to the SQLite database file
            service_name: Name of the service for telemetry
            validator_model_name: Optional model name for validator.
                       If not provided, will try to use MAHILO_POLICY_MODEL or MAHILO_LLM_MODEL env var.
                       If env vars are not set, will use the default model from llm_config.
        """
        self.agents: Dict[str, BaseAgent] = {}
        self.store = SQLiteMessageStore(db_path)
        self.telemetry = MahiloTelemetry(service_name)
        
        # Set up policy manager and validator
        self.policy_manager = PolicyManager(validator_model_name)
        
        # Add default policies
        for policy in create_default_policies(validator_model_name):
            self.policy_manager.add_policy(policy)
            
        self.validator = MessageValidator(self.policy_manager)
        
        # Create message broker with validator
        self.message_broker = MessageBroker(
            secret_key=secret_key,
            store=self.store,
            telemetry=self.telemetry,
            validator=self.validator
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
            event_type=EventType.AGENT_REGISTERED,
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
                event_type=EventType.AGENT_UNREGISTERED,
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
    
    async def send_message_to_agent(self, sender: str, recipient: str, 
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
        await self.message_broker.send_message(envelope)
    
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
        
    # Policy management methods
    
    def add_policy(self, policy: Policy) -> None:
        """Add a policy to the policy manager.
        
        Args:
            policy: The policy to add
        """
        self.policy_manager.add_policy(policy)
        
    def remove_policy(self, policy_name: str) -> None:
        """Remove a policy from the policy manager.
        
        Args:
            policy_name: Name of the policy to remove
        """
        self.policy_manager.remove_policy(policy_name)
        
    def get_policy(self, policy_name: str) -> Optional[Policy]:
        """Get a policy by name.
        
        Args:
            policy_name: Name of the policy to get
            
        Returns:
            The policy if found, None otherwise
        """
        return self.policy_manager.get_policy(policy_name)
        
    def enable_policy(self, policy_name: str) -> None:
        """Enable a policy by name.
        
        Args:
            policy_name: Name of the policy to enable
        """
        self.policy_manager.enable_policy(policy_name)
        
    def disable_policy(self, policy_name: str) -> None:
        """Disable a policy by name.
        
        Args:
            policy_name: Name of the policy to disable
        """
        self.policy_manager.disable_policy(policy_name)
        
    def get_policies(self) -> List[Policy]:
        """Get all policies.
        
        Returns:
            List of all policies
        """
        return self.policy_manager.policies
        
    def get_policy_violations(self, 
                            limit: int = 100, 
                            policy_name: Optional[str] = None) -> List[PolicyViolation]:
        """Get recent policy violations.
        
        Args:
            limit: Maximum number of violations to return
            policy_name: Optional name of policy to filter by
            
        Returns:
            List of policy violations
        """
        violations = self.policy_manager.violation_history
        
        if policy_name:
            violations = [v for v in violations if v.policy_name == policy_name]
            
        # Sort by timestamp (newest first) and limit
        return sorted(violations, key=lambda v: -v.timestamp)[:limit]
        
    def add_heuristic_policy(self, 
                           name: str, 
                           description: str, 
                           policy_function: Callable,
                           priority: int = 0) -> None:
        """Add a heuristic policy.
        
        Args:
            name: Unique name for the policy
            description: Human-readable description of what the policy does
            policy_function: Callable that evaluates messages
            priority: Priority of the policy (higher values = higher priority)
        """
        policy = Policy(
            name=name,
            description=description,
            policy_type=PolicyType.HEURISTIC,
            policy_content=policy_function,
            priority=priority
        )
        self.add_policy(policy)
        
    def add_natural_language_policy(self, 
                                  name: str, 
                                  description: str, 
                                  policy_text: str,
                                  priority: int = 0) -> None:
        """Add a natural language policy.
        
        Args:
            name: Unique name for the policy
            description: Human-readable description of what the policy does
            policy_text: Natural language description of the policy
            priority: Priority of the policy (higher values = higher priority)
        """
        policy = Policy(
            name=name,
            description=description,
            policy_type=PolicyType.NATURAL_LANGUAGE,
            policy_content=policy_text,
            priority=priority
        )
        self.add_policy(policy)