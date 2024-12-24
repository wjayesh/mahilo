from mahilo.agent import BaseAgent
from typing import Any, Dict, List, Callable, Literal, Union
from fastapi import WebSocket
from langgraph.graph import StateGraph
from rich.console import Console
from rich.traceback import install

console = Console()
install()  #

class LanggraphMahiloAgent(BaseAgent):
    """Adapter class to use langgraph agents within the mahilo framework."""
    
    def __init__(self, 
                 langgraph_agent: StateGraph,  # The actual langgraph agent instance
                 type: str = "langgraph",
                 name: str = None,
                 description: str = None,
                 can_contact: List[str] = [],
                 short_description: str = None):
        """Initialize a LanggraphAgent.
        
        Args:
            langgraph_agent: The langgraph agent instance to wrap
            type: The type of agent (e.g. "story_weaver")
            name: Unique name for this agent instance
            description: Long description of the agent
            can_contact: List of agent types this agent can contact
            short_description: Brief description of the agent
        """
        super().__init__(
            type=type,
            name=name,
            description=description,
            can_contact=can_contact,
            short_description=short_description
        )
        self._langgraph_agent = langgraph_agent
        
        self.compiled_graph = self._langgraph_agent.compile()

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Return all tools available to this agent, combining langgraph and mahilo tools."""
        console.print("[bold red] ⚠️  Please use the compiled_graph property to get tools.[/bold red]")
        return []

    async def process_chat_message(self, message: str = None, websockets: List[WebSocket] = []) -> Dict[str, Any]:
        """Process a message using the langgraph agent's invoke method."""
        if not message:
            return {"response": "", "activated_agents": []}

        # Get context from other agents
        other_agent_messages = self._agent_manager.get_agent_messages(self.name, num_messages=7)
        
        message_full = f"{other_agent_messages}"
        available_agents = self.get_contactable_agents_with_description()
        if message:
            message_full += f"\n User: {message}"
            console.print("[bold blue]🤖 Available Agents:[/bold blue]")
            for agent_type, desc in available_agents.items():
                console.print(f"  [green]▪[/green] [cyan]{agent_type}:[/cyan] [dim]{desc}[/dim]")
            message_full += f"\n Available agents to chat with: {available_agents}"
            message_full += f"\n Your Agent Name: {self.name}"

        # Prepare the context for the langgraph agent
        messages = [("user", message_full)]
        messages.append(("system", self.description))

        config = {"configurable": {"thread_id": "1"}}

        response = self.compiled_graph.invoke({"messages": messages}, config, stream_mode="values")

        response_text = response["messages"][-1].content
        
        # Get activated agents
        activated_agents = [
            agent.name for agent in self._agent_manager.get_all_agents() 
            if agent.is_active() and agent.name != self.name
        ]

        print("Activated agents:", activated_agents)
        print("In process_chat_message:", response_text)

        return {
            "response": response_text,
            "activated_agents": activated_agents
        }

    async def process_queue_message(self, message: str = None, websockets: List[WebSocket] = []) -> None:
        """Process a queue message using the langgraph agent."""
        if not message:
            return

        available_agents = self.get_contactable_agents_with_description()
        if message:
            message_full = f"Message from: {message}. Use it to answer the user."
            console.print("[bold blue]🤖 Available Agents:[/bold blue]")
            for agent_type, desc in available_agents.items():
                console.print(f"  [green]▪[/green] [cyan]{agent_type}:[/cyan] [dim]{desc}[/dim]")
            message_full += f"\n Available agents to chat with: {available_agents} "
            message_full += f"Your Agent Name: {self.name}"

        print(f"Queue message for {self.name}: {message_full}")

        messages = [("user", message_full)]
        messages.append(("system", self.description))
        messages.append(("system", "You should only contact other agents if the need be. If you already have info from them, don't call any tools and just return your answer based on their response."))

        config = {"configurable": {"thread_id": "1"}}
        
        # Invoke the langgraph agent
        response = self.compiled_graph.invoke({"messages": messages}, config, stream_mode="values")

        response_text = response["messages"][-1].content
        # send the response to the websockets
        for ws in websockets:
            await ws.send_text(response_text)

        print("In queue fn:", response_text)
