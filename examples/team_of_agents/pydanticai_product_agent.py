from dataclasses import dataclass
from typing import Dict, List

from pydantic import BaseModel

from pydantic_ai import Agent, RunContext


class DatabaseConn:
    """This is a fake database for example purposes.

    In reality, you'd be connecting to an external database
    (e.g. PostgreSQL) to get information about customers.
    """

    @classmethod
    async def get_roadmap(cls, *, product_name: str) -> str | None:
        if product_name == 'mahilo':
            return 'Build mahilo Agents'

@dataclass
class ProductDependencies:
    product_name: str
    db: DatabaseConn

class FeatureAnalysis(BaseModel):
    feature_name: str
    priority: int
    requests_for_human: List[str]
    comments: str

product_agent = Agent(
    'openai:gpt-4o-mini',
    deps_type=ProductDependencies,
    result_type=FeatureAnalysis,
    system_prompt=(
        'You are a product manager in our company,'
        'you are responsible for the product roadmap and feature requests.'
    ),
)

@product_agent.tool
async def analyze_feature_request(ctx: RunContext[ProductDependencies], feature: str) -> str:
    """Analyze viability and impact of requested features"""
    return "Based on analysis, mahilo integration is in our Q3 roadmap, coming in a few months."

@product_agent.tool
async def get_product_roadmap(ctx: RunContext[ProductDependencies]) -> str:
    """Get current product roadmap and timeline"""
    roadmap = await ctx.deps.db.get_roadmap(product_name=ctx.deps.product_name)
    return roadmap

@product_agent.tool
async def analyze_usage_patterns(ctx: RunContext[ProductDependencies], feature: str) -> Dict[str, float]:
    """Analyze how customers are using specific features"""
    return {
        'mahilo integration': 0.5,
        'New feature': 0.3,
    }
