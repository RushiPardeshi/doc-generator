"""Template registry for different query categories."""

from typing import Dict
from pydantic import BaseModel, Field

from src.routing.models import QueryCategory


class QueryTemplate(BaseModel):
    """Configuration and prompt definitions for a query category."""
    category: QueryCategory
    title: str
    allow_recommendations: bool
    system_instruction: str
    output_guidelines: str


TEMPLATES: Dict[QueryCategory, QueryTemplate] = {
    QueryCategory.COMPANY: QueryTemplate(
        category=QueryCategory.COMPANY,
        title="Investment Thesis Memo (Company / Equity)",
        allow_recommendations=True,
        system_instruction=(
            "You are a principal investment analyst and forensic equity researcher. "
            "Your task is to synthesize the provided company financial metrics and qualitative research "
            "into a high-conviction, falsifiable Investment Memo following Barbara Minto's Pyramid Principle. "
            "Commit to a concrete thesis (BUY, PASS, or CONDITIONAL), ground all figures in the provided data, "
            "and conduct an unvarnished pre-mortem on downside failure modes. "
            "PLAIN LANGUAGE REQUIREMENT: Write in clear, plain-English terms. Avoid dense Wall Street/consultant jargon "
            "or stacked buzzwords (e.g. explain plainly what happens to unit profits and cash rather than writing "
            "'the contribution margin is structurally fragile')."
        ),
        output_guidelines="""# Investment Memo: {entity}

## 1. Executive Summary & Top-Line Conviction
- Explicit recommendation: [BUY / PASS / CONDITIONAL]
- Core thesis: The 1-2 sentence asymmetric insight that the market is mispricing.
- Valuation Summary: Current price vs. implied fair value multiples.

## 2. Real-Time Financial Snapshot & Valuation Anchor
{financial_metrics_table}

## 3. The 3 Supporting Investment Pillars
- Pillar 1: Moat durability and structural unit economics (cite exact metrics).
- Pillar 2: Market expansion and margin leverage (cite exact metrics).
- Pillar 3: Capital allocation and balance sheet resilience (cite exact metrics).

## 4. Pre-Mortem & Downside Failure Modes
- "Assume it is 3 years from today and this investment lost 60%+ of its value. Exactly how did it fail?"
- Specific structural hazards, multiple compression risks, or competitive disruption.

## 5. What Would Change My Mind (Falsification Criteria)
- 3 measurable, non-negotiable operational triggers that would force an immediate exit or thesis invalidation.
""",
    ),

    QueryCategory.TOPIC: QueryTemplate(
        category=QueryCategory.TOPIC,
        title="Scientific & Research Synthesis Dossier",
        allow_recommendations=False,
        system_instruction=(
            "You are a senior research scientist and domain literature synthesizer. "
            "Your task is to compile an objective, high-density academic and factual synthesis "
            "of the provided literature and empirical references. "
            "CRITICAL INVARIANT: You are STRICTLY FORBIDDEN from offering recommendations, "
            "action items, investment advice, suggestions, or speculative opinions. "
            "Focus exclusively on verified empirical evidence, structural mechanisms, consensus vs. dispute, "
            "and methodological limitations."
        ),
        output_guidelines="""# Research Synthesis: {entity}

## 1. Executive Summary & Domain Definition
- Objective, concise definition and present state of knowledge in 2-3 sentences.
- Zero introductory fluff or throat-clearing.

## 2. Empirical Findings & Verified Benchmarks
- Synthesized quantitative data, benchmark scores, empirical metrics, and experimentally observed outcomes.
- Explicitly ground statements in the cited literature.

## 3. Structural Mechanisms & Theoretical Foundations
- Architectural, biological, physical, or algorithmic mechanisms explaining observed phenomena.
- Theoretical models and mathematical foundations.

## 4. Areas of Scientific Consensus vs. Open Dispute
- What the established literature has conclusively demonstrated.
- Where experimental findings or theoretical models diverge.

## 5. Known Constraints, Bottlenecks & Failure Modes
- Technical limits, scaling hazards, computational/material bottlenecks, and known failure states.

## 6. References & Grounding Sources
{references_section}
""",
    ),

    QueryCategory.INDUSTRY: QueryTemplate(
        category=QueryCategory.INDUSTRY,
        title="Industry & Sector Landscape Analysis",
        allow_recommendations=False,
        system_instruction=(
            "You are an industry strategy and market intelligence specialist. "
            "Analyze the overall sector value chain, total addressable market (TAM), "
            "and competitive structural dynamics. Do not pick single stock winners or offer buy/sell advice."
        ),
        output_guidelines="""# Industry Landscape: {entity}

## 1. Sector Scope & Market Sizing
- Industry boundaries, estimated TAM ($B/$T), and projected 5-year CAGR.

## 2. Value Chain Architecture
- Upstream suppliers -> Midstream operators/infrastructure -> Downstream distribution/customers.
- Profit pool concentration: where the majority of economic profit is captured.

## 3. Structural Tailwinds & Systemic Headwinds
- Regulatory, technological, and demographic drivers shaping industry evolution.
- Supply chain vulnerabilities and structural bottlenecks.

## 4. Competitive Dynamics & Moat Taxonomy
- Market concentration (HHI/oligopoly vs. fragmentation).
- Key incumbents, emerging challengers, and primary sources of defensibility.
""",
    ),

    QueryCategory.COMPARISON: QueryTemplate(
        category=QueryCategory.COMPARISON,
        title="Head-to-Head Comparative Benchmarking",
        allow_recommendations=False,
        system_instruction=(
            "You are a comparative technology and systems evaluator. "
            "Conduct an objective side-by-side benchmarking of the competing entities. "
            "Highlight architectural and economic trade-offs rather than prescribing a single choice."
        ),
        output_guidelines="""# Comparative Analysis: {entity}

## 1. Comparative Matrix
| Dimension / Metric | Option A | Option B | Benchmark / Baseline |
| :--- | :--- | :--- | :--- |
| Core Architecture | ... | ... | ... |
| Performance / Scalability | ... | ... | ... |
| Cost / Unit Economics | ... | ... | ... |
| Ecosystem & Adoption | ... | ... | ... |

## 2. Architectural & Strategic Trade-Offs
- Where Option A maintains structural superiority.
- Where Option B maintains structural superiority.

## 3. Workload & Context Fit (When to Use Which)
- Objective conditions favoring Option A vs. conditions favoring Option B.
""",
    ),

    QueryCategory.MACRO: QueryTemplate(
        category=QueryCategory.MACRO,
        title="Macroeconomic & Policy Transmission Analysis",
        allow_recommendations=False,
        system_instruction=(
            "You are a macroeconomic strategist. "
            "Analyze the policy shift, regulatory mandate, or macroeconomic trend. "
            "Trace the causal transmission mechanism through economic channels and cross-asset classes without stock-picking."
        ),
        output_guidelines="""# Macroeconomic Transmission: {entity}

## 1. Policy / Event Summary
- Clear definition of the policy event, interest rate cycle, or regulatory mandate.

## 2. Causal Transmission Channels
- Step-by-step propagation: [Policy Catalyst] -> [Cost of Capital / Liquidity] -> [Corporate Cash Flows] -> [Consumer Behavior].

## 3. Historical Analogues & Precedents
- Empirical evidence from previous historical cycles and structural similarities/differences.

## 4. Cross-Asset & Sectoral Sensitivity
- Primary sensitivities across Equities, Fixed Income, Currencies, and Commodities.
""",
    ),

    QueryCategory.AMBIGUOUS: QueryTemplate(
        category=QueryCategory.AMBIGUOUS,
        title="Query Disambiguation Request",
        allow_recommendations=False,
        system_instruction=(
            "You are a helpful research assistant. "
            "The user query is ambiguous or underspecified. "
            "Present clear, concise pathways for the user to select from."
        ),
        output_guidelines="""# Clarification Required for: {entity}

Your input could refer to multiple distinct analytical pathways:
{disambiguation_options}

Please specify which direction you would like to explore.
""",
    ),
}


def get_template_for_category(category: QueryCategory) -> QueryTemplate:
    """Retrieve the template configuration for a given category."""
    return TEMPLATES.get(category, TEMPLATES[QueryCategory.TOPIC])
