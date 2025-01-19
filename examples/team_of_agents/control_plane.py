from mahilo import BaseAgent, AgentManager, ServerManager
from mahilo.integrations.pydanticai.agent import PydanticAIAgent
from mahilo.integrations.langgraph.agent import LangGraphAgent
import os

from pydanticai_product_agent import DatabaseConn, ProductDependencies, product_agent
from langgraph_marketing_agent import graph_builder
from mahilo_sales_agent import tools as sales_tools

product_agent_prompt = """
you only have access to sales and marketing agents. dont make agents up.
when asked about the status of a feature, use the analyze_feature_request tool and respond back to the agent that asked you the question.
you should use the chat_with_agent function to respond back to an agent that asked you a question.
You can then request approvals from your user (human) when you feel there's a need to
prioritize a feature. DONT ASK QUESTIONS YOURSELF, this is just a demo, assume stuff when there's not enough information.
"""

marketing_agent_prompt = """
When notified of new features, research trending topics and generate a content calendar. Give your recommendations on what to do, to your user (human). 
Use the analyze_content_performance tool when asked about the performance of the content. You should also ask the sales agent for what channels have brought in more leads.
"""

sales_agent_prompt = """
When asked about analysing calls, gather user feedback on it and present to your user (human).
If you spot a feature that has been requested or has some interest in public, ask your human if you can ask the product agent about its status.
For all other scenarios, only call tools or actions when asked to do so. Don't do everything together, wait for prompts. dont call other tools.
"""

def main():
    port = int(os.getenv("PORT", "8000"))
    server_id = os.getenv("SERVER_ID")

    prod_agent = PydanticAIAgent(
        pydantic_agent=product_agent,
        name="ProductAgent",
        description=product_agent_prompt,
        can_contact=[],
        short_description="Product agent",
    )

    marketing_agent = LangGraphAgent(
        langgraph_agent=graph_builder,
        name="MarketingAgent",
        description=marketing_agent_prompt,
        can_contact=[],
        short_description="Marketing agent",
    )

    sales_agent = BaseAgent(
        name="SalesAgent",
        type="sales_agent",
        description=sales_agent_prompt,
        short_description="Sales agent",
        tools=sales_tools,
    )

    team = AgentManager()
    team.register_agent(prod_agent)
    team.register_agent(marketing_agent)
    team.register_agent(sales_agent)

    # activate the pydantic agent with the right dependencies
    prod_agent.activate(dependencies=ProductDependencies(product_name="Mahilo", db=DatabaseConn()))
    # activate the langgraph agent with a thread id
    marketing_agent.activate(server_id=server_id)
    # activate the base agent with no dependencies
    sales_agent.activate()

    server = ServerManager(team)
    server.run(port=port)

if __name__ == "__main__":
    main()
