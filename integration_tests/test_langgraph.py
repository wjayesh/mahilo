import asyncio
from typing import Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from mahilo.agent import BaseAgent
from mahilo.agent_manager import AgentManager
from mahilo.integrations.langgraph.agent import LanggraphMahiloAgent
from mahilo.integrations.langgraph.tools import get_chat_with_agent_tool_langgraph
from mahilo.server import ServerManager

memory = MemorySaver()

class State(TypedDict):
    messages: Annotated[list, add_messages]


graph_builder = StateGraph(State)

from langchain_core.tools import tool
import random

@tool
def query_zenml_knowledge(query: str, max_results: int =3, similarity_threshold: float=0.7):
  """Query knowledge about the product ZenML"""
  responses = [
      "Yes, ZenML can do that through its powerful ZenML Hub",
      "I can't find any information about this in the given documentation"
  ]

  response = random.choices(responses, weights=[0.5, 0.5], k=1)

  return response[0]


chat_with_agent_tool = get_chat_with_agent_tool_langgraph()
tools = [query_zenml_knowledge, chat_with_agent_tool]
llm = ChatOpenAI(model="gpt-4o-mini")
llm_with_tools = llm.bind_tools(tools)


def chatbot(state: State):
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)
graph_builder.add_edge("tools", "chatbot")
graph_builder.set_entry_point("chatbot")

# graph = graph_builder.compile()
# response = graph.invoke({"messages": [("user", "hi tell me about zenml")]})

# breakpoint()

agent = LanggraphMahiloAgent(
    langgraph_agent=graph_builder,
    type="langgraph",
    name="LanggraphAgent",
    description="A general Langgraph agent.",
    can_contact=[],
    short_description="A Langgraph agent"
)

agent_mahilo = BaseAgent(
    type="WeatherAgent",
    name="WeatherAgent",
    description="A weather agent. Whenever someone asks about the weather, ask your human to tell you the weather.",
    can_contact=[],
    short_description="A weather agent"
)


manager = AgentManager()
manager.register_agent(agent_mahilo)
manager.register_agent(agent)

# server_id is the thread_id for the langgraph agent
# if not provided, it will be set to "1"
agent.activate(server_id="1")

# asyncio.run(agent.process_chat_message(message="hi tell me about zenml", websockets=[]))

server = ServerManager(manager)

if __name__ == "__main__":
    server.run()