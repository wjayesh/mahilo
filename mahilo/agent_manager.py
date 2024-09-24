from typing import Dict, List
from .agent import BaseAgent


class AgentManager:
    """A class to manage agents of different types.
    
    This class should also have functions that can register new AgentTypes and keep track of them.
    """
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the AgentManager."""
        # if the agent is already registered, raise an error
        if agent.TYPE in self.agents:
            raise ValueError(f"Agent of type {agent.TYPE} is already registered.")
        agent._agent_manager = self
        self.agents[agent.TYPE] = agent

    def get_agent(self, agent_type: str) -> BaseAgent:
        """Return the agent of the given type."""
        return self.agents.get(agent_type)
    
    def get_all_agent_types(self) -> List[str]:
        """Return a list of all registered agent types."""
        return list(self.agents.keys())

    def get_all_agents(self) -> List[BaseAgent]:
        """Return a list of all registered agents."""
        return list(self.agents.values())

    def is_agent_registered(self, agent_type: str) -> bool:
        """Check if an agent of the given type is registered."""
        return agent_type in self.agents

    def unregister_agent(self, agent_type: str) -> None:
        """Unregister the agent of the given type."""
        if agent_type in self.agents:
            del self.agents[agent_type]

    def unregister_all_agents(self) -> None:
        """Unregister all agents."""
        self.agents.clear()

    def get_agent_types_with_description(self) -> Dict[str, str]:
        """Return a list of all registered agent types with their descriptions."""
        # for the description, we only want the short description
        # the short description first 0 words
        return {agent.TYPE: " ".join(agent.description.split(" ")[:0]) for agent in self.agents.values()}
    
    # get last 3 messages from all agents' sessions except the current agent.
    def get_agent_messages(self, agent_type: str) -> str:
        """Return the last 3 messages from all agents' sessions except the current agent.
        
        Format of the messages: "<agent_name>: <message>"
        """
        messages = ''
        for agent in self.agents.values():
            if agent.TYPE != agent_type and agent._session:
                agent_messages = agent._session.get_last_n_messages(3)
                agent_name = agent.TYPE
                messages += (f"Other Conversations: {agent_name}: ")
                messages += "\n".join([f"{message['role']}: {message['content']}" for message in agent_messages])
                messages += "\n"
        return messages
        
    def populate_can_contact_for_agents(self) -> None:
        """Populate the can_contact list for all agents."""
        # if the can_contact is empty, set it to all agents
        for agent in self.agents.values():
            if not agent.can_contact:
                agent.can_contact = self.get_all_agent_types()