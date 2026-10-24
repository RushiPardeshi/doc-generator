"""Intent classification and routing engine for user queries."""

import re
from typing import Optional, List
from src.routing.models import QueryCategory, RoutingDecision
from src.llm.base import LLMProvider

ROUTER_SYSTEM_INSTRUCTION = """You are an expert query classification router for an analytical intelligence platform.
Your objective is to inspect the user's input and classify it accurately into one of the following strict categories:

1. 'company': The input is a specific corporation, company, or public stock ticker (e.g. "Apple", "Nvidia", "MSFT", "Palantir").
   - This is an investment-based problem.
   - Real-time financial metrics are required.
   - Actionable investment recommendations and bull/bear theses ARE allowed (`allow_recommendations: true`).

2. 'topic': The input is a general or specialized research topic, scientific question, academic domain, or technological concept (e.g. "Quantum error correction", "CRISPR off-target mutations", "Solid-state electrolyte degradation", "History of Renaissance banking").
   - This is a research compilation problem.
   - Academic references, scholarly citations, and factual synthesis are required.
   - INVARIANT: Recommendations, investment advice, and suggestions are STRICTLY FORBIDDEN (`allow_recommendations: false`).

3. 'industry': The input explores an entire industry, market sector, value chain, or thematic vertical rather than a single company (e.g. "Semiconductor lithography market", "GLP-1 obesity drug landscape", "US commercial nuclear power").
   - Needs market sizing (TAM/CAGR) and value chain mapping.
   - Single-stock buy/sell recommendations are forbidden (`allow_recommendations: false`).

4. 'comparison': The input asks for a head-to-head comparison between two or more companies, technologies, or frameworks (e.g. "Snowflake vs Databricks", "Nvidia vs AMD", "PyTorch vs JAX").
   - Comparative metric tables and trade-offs are required.

5. 'macro': The input asks about macroeconomic trends, monetary policy, geopolitics, or broad regulatory shifts (e.g. "Impact of Fed rate cuts on commercial real estate", "EU AI Act compliance obligations").
   - Transmission mechanisms and historical precedents are required (`allow_recommendations: false`).

6. 'ambiguous': The input is an isolated single word or polysemous phrase that could mean completely different things without context (e.g. "Apple" without context, "Mercury", "Block").
   - Provide 2-3 disambiguation options for the user.

Ensure `allow_recommendations` is true ONLY for 'company' and false for 'topic', 'industry', and 'macro'.
"""


def _heuristic_classify(query: str) -> RoutingDecision:
    """Deterministic heuristic classification fallback when LLM is unavailable or for rapid parsing."""
    q_clean = query.strip()
    q_lower = q_clean.lower()

    # Ambiguity check: single word polysemous terms without ticker/context
    ambiguous_keywords = {"mercury", "block", "square", "target", "meta"}
    if q_lower in ambiguous_keywords and len(q_clean.split()) == 1:
        return RoutingDecision(
            query=q_clean,
            category=QueryCategory.AMBIGUOUS,
            primary_entities=[q_clean],
            tickers=[],
            allow_recommendations=False,
            data_sources=["serp_web"],
            disambiguation_options=[
                f"Company analysis for {q_clean.capitalize()} (financial metrics & investment thesis)",
                f"Scientific or general research on '{q_clean}' (scholarly references & technical overview)",
            ],
            reasoning=f"The term '{q_clean}' is polysemous and lacks contextual qualifiers.",
        )

    # Comparison check: " vs " or " versus "
    if " vs " in q_lower or " vs. " in q_lower or " versus " in q_lower:
        parts = re.split(r"\s+(?:vs\.?|versus)\s+", q_clean, flags=re.IGNORECASE)
        entities = [p.strip() for p in parts if p.strip()]
        return RoutingDecision(
            query=q_clean,
            category=QueryCategory.COMPARISON,
            primary_entities=entities,
            tickers=[],
            allow_recommendations=False,
            data_sources=["financial_metrics", "serp_web"],
            reasoning="Query compares multiple entities head-to-head.",
        )

    # Macro / Policy check
    macro_patterns = [
        r"\bfed\b", r"interest rate", r"inflation", r"gdp", r"treasury yield",
        r"macroeconomic", r"monetary policy", r"tariff", r"regulation", r"eu ai act",
    ]
    if any(re.search(pat, q_lower) for pat in macro_patterns):
        return RoutingDecision(
            query=q_clean,
            category=QueryCategory.MACRO,
            primary_entities=[q_clean],
            tickers=[],
            allow_recommendations=False,
            data_sources=["serp_web", "serp_scholar"],
            reasoning="Query pertains to macroeconomic indicators, monetary policy, or broad regulatory frameworks.",
        )

    # Industry / Sector check
    industry_patterns = [
        r"market\b", r"industry\b", r"sector\b", r"landscape\b", r"value chain",
        r"market size", r"tam\b", r"cagr\b", r"ecosystem\b",
    ]
    if any(re.search(pat, q_lower) for pat in industry_patterns):
        return RoutingDecision(
            query=q_clean,
            category=QueryCategory.INDUSTRY,
            primary_entities=[q_clean],
            tickers=[],
            allow_recommendations=False,
            data_sources=["serp_web", "financial_metrics"],
            reasoning="Query focuses on industry dynamics, market sizing, or sector landscape.",
        )

    # Known stock ticker detection (e.g., AAPL, NVDA, TSLA, MSFT, GOOGL, AMZN) or company patterns
    ticker_match = re.match(r"^[A-Z]{1,5}$", q_clean)
    company_indicators = [
        r"\binc\b", r"\bcorp\b", r"\bcorporation\b", r"\bltd\b", r"\bco\b",
        r"\btechnologies\b", r"\bsystems\b", r"\bholdings\b", r"\bvaluation\b",
        r"\bstock\b", r"\bshares\b", r"\bearnings\b", r"\b10-k\b", r"\bquarterly results\b",
    ]
    is_common_company = q_lower in {
        "apple", "nvidia", "microsoft", "google", "alphabet", "amazon", "tesla",
        "meta", "palantir", "amd", "intel", "broadcom", "qualcomm", "netflix",
        "uber", "airbnb", "snowflake", "salesforce", "oracle", "adobe",
    }

    if ticker_match or is_common_company or any(re.search(ind, q_lower) for ind in company_indicators):
        ticker = q_clean.upper() if ticker_match else ""
        return RoutingDecision(
            query=q_clean,
            category=QueryCategory.COMPANY,
            primary_entities=[q_clean],
            tickers=[ticker] if ticker else [],
            allow_recommendations=True,
            data_sources=["financial_metrics", "serp_web"],
            reasoning="Query targets a specific corporate entity or equity investment problem.",
        )

    # Default to Topic: pure research compiled without recommendations
    return RoutingDecision(
        query=q_clean,
        category=QueryCategory.TOPIC,
        primary_entities=[q_clean],
        tickers=[],
        allow_recommendations=False,
        data_sources=["serp_scholar", "semantic_scholar", "serp_web"],
        reasoning="Query is a general or scientific research topic requiring compiled citations and synthesis with no recommendations.",
    )


def classify_query(
    query: str,
    provider: Optional[LLMProvider] = None,
) -> RoutingDecision:
    """
    Classify a user query to determine whether it is a company investment problem,
    a pure research topic, an industry landscape, a comparison, a macro topic, or ambiguous.
    """
    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    query_str = query.strip()

    if provider:
        prompt = f"Classify the following query according to the instructions:\n\nQuery: \"{query_str}\""
        try:
            decision = provider.complete_structured(
                prompt=prompt,
                schema=RoutingDecision,
                system_instruction=ROUTER_SYSTEM_INSTRUCTION,
                temperature=0.0,
            )
            # Strict safety invariant: Topic, Industry, and Macro must NEVER allow recommendations
            if decision.category in (QueryCategory.TOPIC, QueryCategory.INDUSTRY, QueryCategory.MACRO):
                decision.allow_recommendations = False
            elif decision.category == QueryCategory.COMPANY:
                decision.allow_recommendations = True

            return decision
        except Exception:
            # Fall back to heuristic classification if LLM fails or is rate-limited
            pass

    return _heuristic_classify(query_str)
