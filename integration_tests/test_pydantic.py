"""Small but complete example of using PydanticAI to build a support agent for a bank.

Run with:

    uv run -m pydantic_ai_examples.bank_support
"""

from dataclasses import dataclass

from pydantic import BaseModel, Field

from pydantic_ai import Agent, RunContext

from mahilo.agent import BaseAgent
from mahilo.agent_manager import AgentManager
from mahilo.integrations.pydanticai.agent import PydanticAIAgent
from mahilo.server import ServerManager


class DatabaseConn:
    """This is a fake database for example purposes.

    In reality, you'd be connecting to an external database
    (e.g. PostgreSQL) to get information about customers.
    """

    @classmethod
    async def customer_name(cls, *, id: int) -> str | None:
        if id == 123:
            return 'John'

    @classmethod
    async def customer_balance(cls, *, id: int, include_pending: bool) -> float:
        if id == 123:
            return 123.45
        else:
            raise ValueError('Customer not found')


@dataclass
class SupportDependencies:
    customer_id: int
    db: DatabaseConn


class SupportResult(BaseModel):
    support_advice: str = Field(description='Advice returned to the customer')
    block_card: bool = Field(description='Whether to block their')
    risk: int = Field(description='Risk level of query', ge=0, le=10)


support_agent = Agent(
    'openai:gpt-4o',
    deps_type=SupportDependencies,
    result_type=SupportResult,
    system_prompt=(
        'You are a support agent in our bank, give the '
        'customer support and judge the risk level of their query. '
        "Reply using the customer's name."
    ),
)


@support_agent.system_prompt
async def add_customer_name(ctx: RunContext[SupportDependencies]) -> str:
    customer_name = await ctx.deps.db.customer_name(id=ctx.deps.customer_id)
    return f"The customer's name is {customer_name!r}"


@support_agent.tool
async def customer_balance(
    ctx: RunContext[SupportDependencies], include_pending: bool
) -> str:
    """Returns the customer's current account balance."""
    balance = await ctx.deps.db.customer_balance(
        id=ctx.deps.customer_id,
        include_pending=include_pending,
    )
    return f'${balance:.2f}'

mahilo_pydantic_agent = PydanticAIAgent(
    pydantic_agent=support_agent,
    name="SupportAgent",
    description="You can talk to other agents as needed too to answer user questions. When you do so, let the user know that you are talking to another agent.",
    can_contact=[],
    short_description="",
)

mahilo_base_agent = BaseAgent(
    name="WeatherAgent",
    type="weather_agent",
    description="When someone asks you about the weather, ask your human for it.",
    can_contact=[],
    short_description="",
)

manager = AgentManager()
manager.register_agent(mahilo_pydantic_agent)
manager.register_agent(mahilo_base_agent)

mahilo_pydantic_agent.activate(dependencies=SupportDependencies(customer_id=123, db=DatabaseConn()))

server = ServerManager(manager)


if __name__ == '__main__':
    server.run()