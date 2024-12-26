from typing import Dict, List
from .agent import BaseAgent
from .registry import GlobalRegistry


class AgentManager:
    """A class to manage agents of different types.
    
    This class should also have functions that can register new AgentTypes and keep track of them.
    """
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        # Register self with global registry
        GlobalRegistry.set_agent_registry(self)

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the AgentManager."""
        if agent.name in self.agents:
            raise ValueError(f"Agent with name {agent.name} is already registered.")
        agent._agent_manager = self
        self.agents[agent.name] = agent

    def get_agent(self, agent_name: str) -> BaseAgent:
        """Return the agent of the given name."""
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
            del self.agents[agent_name]

    def unregister_all_agents(self) -> None:
        """Unregister all agents."""
        self.agents.clear()

    def get_agent_types_with_description(self) -> Dict[str, str]:
        """Return a list of all registered agent types with their descriptions."""
        return {agent.name: agent.short_description for agent in self.agents.values()}
    
    # get last 3 messages from all agents' sessions except the current agent.
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