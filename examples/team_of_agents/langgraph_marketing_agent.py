from typing import Annotated, Dict, List

from langchain_openai import ChatOpenAI
from typing_extensions import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from mahilo.integrations.langgraph.tools import get_chat_with_agent_tool_langgraph

memory = MemorySaver()

class State(TypedDict):
    messages: Annotated[list, add_messages]

graph_builder = StateGraph(State)

from langchain_core.tools import tool

@tool
def analyze_content_performance(content: str) -> str:
  """Analyze the performance of the content across social media platforms"""
  return "The content is performing well on LinkedIn."

@tool
def research_trending_topics(industry: str) -> List[str]:
    """Research current trending topics in the industry"""
    return ["Lot of buzz around mahilo agents and its multi-agent capabilities"]

@tool
def generate_content_calendar(timeframe: str) -> Dict[str, str]:
    """Create a content calendar based on trends and performance"""
    return {
        "January": "Mahilo Agents: Multi-Agent Capabilities",
        "February": "Integrations with mahilo",
    }


chat_with_agent_tool = get_chat_with_agent_tool_langgraph()
tools = [analyze_content_performance, research_trending_topics, generate_content_calendar, chat_with_agent_tool]
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
