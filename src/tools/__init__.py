"""Tools package for external live metrics and scholarly research retrieval."""

from src.tools.financial_metrics import (
    CompanyFinancialMetrics,
    fetch_financial_metrics,
)
from src.tools.serp_research import (
    ResearchReference,
    fetch_serp_scholar_references,
    fetch_semantic_scholar_references,
    fetch_authoritative_research,
    compile_references_to_dossier_section,
)

__all__ = [
    "CompanyFinancialMetrics",
    "fetch_financial_metrics",
    "ResearchReference",
    "fetch_serp_scholar_references",
    "fetch_semantic_scholar_references",
    "fetch_authoritative_research",
    "compile_references_to_dossier_section",
]
