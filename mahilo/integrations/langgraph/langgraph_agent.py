from mahilo.agent import BaseAgent
from typing import Any, Dict, List, Callable, Literal, Union
from fastapi import WebSocket
from langgraph.graph import StateGraph

class LanggraphMahiloAgent(BaseAgent):
    """Adapter class to use langgraph agents within the mahilo framework."""
    
    def __init__(self, 
                 langgraph_agent: StateGraph,  # The actual langgraph agent instance
                 main_node_name: str,
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
        
        # Add the base mahilo tools to the langgraph agent
        # self._add_mahilo_tools(main_node_name)

        self.compiled_graph = self._langgraph_agent.compile()

    def _add_mahilo_tools(self, main_node_name: str) -> None:
        """Add mahilo's chat_with_agent and contact_human tools to the langgraph agent."""
        # decorate self.chat_with_agent with @tool from langgraph
        from langchain_core.tools import tool
        from langgraph.prebuilt import ToolNode, tools_condition
        from langchain_core.messages import AnyMessage
        from pydantic import BaseModel

        # decorate self.chat_with_agent with @tool from langgraph
        self.chat_with_agent_lg = tool(self.chat_with_agent)
        # not adding the contact_human tool to the langgraph agent
        # as passing params(websockets) at runtime is not supported by langgraph

        mahilo_tools_node = ToolNode(
            tools=[self.chat_with_agent_lg],
            name="mahilo_tools"
        )
        self._langgraph_agent.add_node(mahilo_tools_node)

        def tools_mahilo_condition(
            state: Union[list[AnyMessage], dict[str, Any], BaseModel],
            messages_key: str = "messages",
        ) -> Literal["tools", "__end__"]:
            """Use in the conditional_edge to route to the ToolNode if the last message"""
            if isinstance(state, list):
                ai_message = state[-1]
            elif isinstance(state, dict) and (messages := state.get(messages_key, [])):
                ai_message = messages[-1]
            elif messages := getattr(state, messages_key, []):
                ai_message = messages[-1]
            else:
                raise ValueError(f"No messages found in input state to tool_edge: {state}")
            if hasattr(ai_message, "tool_calls") and len(ai_message.tool_calls) > 0:
                breakpoint()
                if ai_message.tool_calls[0]["name"] == "chat_with_agent":
                    return "mahilo_tools"
            return "__end__"

        self._langgraph_agent.add_conditional_edges(
            main_node_name,
            tools_mahilo_condition,
        )

    @property
    def tools(self) -> List[Dict[str, Any]]:
        """Return all tools available to this agent, combining langgraph and mahilo tools."""
        breakpoint()
        return self._langgraph_agent.nodes["tools"].tools

    async def process_chat_message(self, message: str = None, websockets: List[WebSocket] = []) -> Dict[str, Any]:
        """Process a message using the langgraph agent's invoke method."""
        if not message:
            return {"response": "", "activated_agents": []}

        # Get context from other agents
        other_agent_messages = self._agent_manager.get_agent_messages(self.TYPE, num_messages=7)
        
        message_full = f"{other_agent_messages}"
        available_agents = self.get_contactable_agents_with_description()
        if message:
            message_full += f"\n User: {message}"
            print("Available agents to chat with:", available_agents)
            message_full += f"\n Available agents to chat with: {available_agents}"

        # Prepare the context for the langgraph agent
        messages = [("user", message_full)]

        # breakpoint()
        response = self.compiled_graph.invoke({"messages": messages}, stream_mode="values")

        print("Response:", response)
        breakpoint()
        
        response_text = response["messages"][-1].content
        print("Response text:", response_text)

        # send the response to the websockets
        for ws in websockets:
            await ws.send_text(response_text)

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

        queue_message = f"Pending messages: {message}"
        
        messages = [{"role": "user", "content": queue_message}]

        # Invoke the langgraph agent
        response = await self._langgraph_agent.invoke({"messages": messages})

        # send the response to the websockets
        for ws in websockets:
            await ws.send_text(response)

        print("In queue fn:", response)
