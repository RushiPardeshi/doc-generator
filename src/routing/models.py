"""Models and schemas for query routing and intent classification."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class QueryCategory(str, Enum):
    """Core categories identifying what is asked of the system."""
    COMPANY = "company"         # Single company/equity investment problem (uses present metrics, actionable thesis)
    TOPIC = "topic"             # Pure research topic (compiled research only, strictly zero recommendations)
    INDUSTRY = "industry"       # Industry / sector value chain & TAM (no individual stock recommendations)
    COMPARISON = "comparison"   # Head-to-head comparison between 2+ entities/technologies
    MACRO = "macro"             # Macroeconomic, monetary policy, or regulatory transmission
    AMBIGUOUS = "ambiguous"     # Polysemous or underspecified term requiring user disambiguation


class RoutingDecision(BaseModel):
    """Structured decision output from the Intent Router."""
    query: str = Field(description="The original user query.")
    category: QueryCategory = Field(description="The classified query category.")
    primary_entities: List[str] = Field(
        default_factory=list,
        description="List of primary entities, companies, or concepts identified."
    )
    tickers: List[str] = Field(
        default_factory=list,
        description="Public stock tickers identified (e.g., ['NVDA', 'AAPL']), if applicable."
    )
    allow_recommendations: bool = Field(
        description="True ONLY if the query is company/investment based; False for research topics, industry, or macro."
    )
    data_sources: List[str] = Field(
        default_factory=list,
        description="Data sources needed: ['financial_metrics', 'serp_scholar', 'serp_web', 'semantic_scholar']."
    )
    disambiguation_options: Optional[List[str]] = Field(
        default=None,
        description="Options to present to the user if the category is AMBIGUOUS."
    )
    reasoning: str = Field(
        description="Brief 1-2 sentence justification for this routing classification."
    )
