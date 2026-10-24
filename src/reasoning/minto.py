"""Grounded Minto Pyramid synthesis with cited claims and derived falsification triggers."""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field

from src.reasoning.claims import GroundedClaim
from src.reasoning.debate import CandidateThesis, DebateArbitrationResult, ThesisStance
from src.llm.base import LLMProvider


class MintoPillar(BaseModel):
    """One of the three core pillars of the Minto Pyramid."""
    headline: str = Field(description="Crisp, assertion-driven pillar title (e.g. 'Multi-Product Cross-Selling Drives 146% NRR')")
    argument: str = Field(description="Explanatory prose defending this pillar, citing claim IDs like [C1], [C4]")
    cited_claim_ids: List[str] = Field(description="List of Claim IDs referenced in this pillar, e.g. ['C1', 'C4']")
    metrics_cited: List[str] = Field(description="Specific metrics from the claims used in this pillar, e.g. ['$153.3 million', '146%']")


class MintoDraft(BaseModel):
    """Executive decision memo structured strictly according to Barbara Minto's Pyramid Principle."""
    company_name: str = Field(description="Name of the target subject, company, technology, proposal, or research topic")
    recommendation: ThesisStance = Field(description="RECOMMEND/BUY, CONDITIONAL, or REJECT/PASS")
    executive_thesis: str = Field(
        description="Paragraph 1 Answer-First core thesis and executive conclusion. Zero throat-clearing."
    )
    pillar_1: MintoPillar = Field(description="First supporting structural pillar")
    pillar_2: MintoPillar = Field(description="Second supporting structural pillar")
    pillar_3: MintoPillar = Field(description="Third supporting structural pillar")
    key_risks: List[str] = Field(
        description="Top 3 unvarnished fatal risks, failure modes, or structural bottlenecks from the pre-mortem"
    )
    what_would_change_my_mind: List[str] = Field(
        description="2-3 explicit falsification triggers derived directly from verified claim metrics"
    )


MINTO_SYNTHESIZER_SYSTEM = """You are an elite research director and analytical thinker drafting an Executive Research Synthesis & Thesis.
You write according to Barbara Minto's Pyramid Principle: ANSWER-FIRST, followed by exactly 3 supporting pillars, structural limits/trade-offs, and falsification criteria.

CRITICAL INVARIANTS:
1. ANSWER-FIRST: Paragraph 1 is the core finding and central thesis. Do NOT start with historical throat-clearing, introductory padding, or generic definitions.
2. RESEARCH FOCUS (NO ARTIFICIAL PROCUREMENT DECISIONS):
   - For pure research subjects (scientific models, ML architectures like LIIF, technologies, concepts), focus strictly on synthesizing the research: what is the core mechanism, what do benchmarks prove, what are the structural constraints, and what is the operating envelope?
   - Do NOT pretend to make an IT deployment, enterprise adoption, or stock purchase decision unless specifically instructed.
3. CITATION DISCIPLINE: Every single supporting pillar MUST cite relevant Claim IDs (e.g. [C1], [C5]) and utilize only the verified metrics and empirical evidence provided in those claims.
4. ZERO INVENTED NUMBERS: Every measurement, number, percentage, and metric you write MUST originate from the cited claims. Never fabricate benchmark metrics or estimates.
5. FALSIFICATION TRIGGERS: 'What Would Change My Mind' (or Falsification Boundaries) must define quantifiable triggers anchored to the claims (e.g., 'If metric X degrades from Y below Z [C#]').
6. SCANNABLE MARKDOWN & AMPLE NEWLINES:
   - Always put a blank line (double newline) after every topic, heading, sub-heading, and bullet item.
   - Break arguments into short, digestible paragraphs (maximum 2-3 sentences each) separated by double newlines. Never write unbroken walls of text.
   - Format multi-point conditions, guardrails, or failure triggers as clean markdown bullet lists with bold lead-ins (e.g., '- **Constraint Name**: details [C#]'), NEVER as run-on inline sentences like '(1) X, (2) Y, (3) Z'.
   - When contrasting quantitative figures across operational regimes (e.g. Baseline vs. Accelerated vs. Degraded), present the comparison in a clean markdown table.
7. PLAIN LANGUAGE & CAUSAL CLARITY:
   - State findings, unit economics, and failure modes in plain, direct English. Avoid dense buzzwords and pretentious financial shorthand.
   - Ground abstract concepts in concrete operational realities (e.g., explain what happens to money, customers, or systems rather than writing "the contribution margin is structurally fragile" or "exhibits asymmetric downside vector").
8. ZERO META-TALK & PROMPT LEAKAGE:
   - Never write about the memo, prompt, or thesis itself. FORBIDDEN: "The thesis survives only within these guardrails", "The argument holds", "opinion-based heuristic, not a rigorously derived cost model".
   - Speak exclusively about the actual company, technology, costs, and data.
9. KEEP CONCRETE EXAMPLES & NUMBERS (NO ABSTRACT OBFUSCATION):
   - When cited claims contain specific dollar ranges, credit rates, or row counts, retain those exact numbers in your explanation. Never replace concrete metrics with vague phrases like "cell density and provider mix" or "compounding capabilities".
   - Use subject-first sentences (e.g., "Clay costs $149–$800/month...", not "Above this threshold, and specifically for teams with..."). Keep sentences short and digestible.
"""


def synthesize_minto_draft(
    company_name: str,
    stance: ThesisStance,
    selected_thesis: Optional[CandidateThesis],
    debate_result: DebateArbitrationResult,
    claims: List[GroundedClaim],
    provider: LLMProvider,
    mode: str = "research",
) -> MintoDraft:
    """Synthesize a structured Minto Pyramid draft memo from debate results and verified claims."""
    claims_text = "\n".join(
        f"[{c.id}] ({c.claim_type.value}): {c.statement}" + (f" | Metric: {c.metric_or_data}" if c.metric_or_data else "")
        for c in claims
    )

    thesis_info = ""
    if selected_thesis:
        thesis_info = (
            f"Selected Thesis: {selected_thesis.headline}\n"
            f"Core Mechanism: {selected_thesis.core_mechanism}\n"
            f"Primary Vulnerability: {selected_thesis.primary_vulnerability}\n"
        )
    else:
        thesis_info = "All candidate theses failed the adversarial critique. Synthesize an unvarnished skeptical/refuted thesis.\n"

    premortem_summary = debate_result.arbitration_summary
    fatal_flaws = []
    falsification_hints = []
    for attack in debate_result.attacks:
        fatal_flaws.extend(attack.fatal_flaws)
        falsification_hints.extend(attack.falsification_triggers)

    if mode == "research":
        prompt = f"""Synthesize an Answer-First Research Synthesis & Thesis for {company_name}.
Focus on the core technical mechanism, empirical benchmark results, structural constraints, and falsification boundaries. Do NOT frame this as an IT procurement, business purchase, or deploy/reject decision.
Write with subject-first sentences and preserve concrete metrics from the claims. Do not write meta-commentary like 'the thesis survives within these guardrails'.

SYNTHESIS STATUS: {stance.value}
{thesis_info}
CRITIQUE / PRE-MORTEM SUMMARY: {premortem_summary}
EXPOSED STRUCTURAL LIMITS / BOTTLENECKS: {', '.join(fatal_flaws[:5])}
CANDIDATE FALSIFICATION TRIGGERS: {', '.join(falsification_hints[:5])}

VERIFIED CLAIMS (USE THESE EXACT METRICS AND CITE IDS [C#]):
{claims_text}
"""
    else:
        prompt = f"""Draft a Minto Pyramid Research & Decision Memo for {company_name}.
Write with subject-first sentences and preserve concrete pricing and numbers from the claims. Do not write meta-commentary like 'the thesis survives within these guardrails' or 'heuristic vs cost model'.

DECISION / STANCE: {stance.value}
{thesis_info}
PRE-MORTEM SUMMARY: {premortem_summary}
EXPOSED FATAL FLAWS: {', '.join(fatal_flaws[:5])}
CANDIDATE FALSIFICATION TRIGGERS: {', '.join(falsification_hints[:5])}

VERIFIED CLAIMS (USE THESE EXACT METRICS AND CITE IDS [C#]):
{claims_text}
"""
    draft = provider.complete_structured(
        prompt=prompt,
        schema=MintoDraft,
        system_instruction=MINTO_SYNTHESIZER_SYSTEM,
        temperature=0.2,
    )
    return draft


def format_minto_to_markdown(draft: MintoDraft, mode: str = "research") -> str:
    """Format a MintoDraft object into clean, human-readable markdown prose with strict newline discipline."""
    if mode == "research":
        title_header = f"# Research Synthesis & Thesis: {draft.company_name}"
        status_line = f"**Synthesis Status**: `{draft.recommendation.value}`"
        section1_title = "## 1. Executive Research Thesis (Answer-First)"
        section2_title = "## 2. Core Empirical Findings & Architectural Pillars"
        section3_title = "## 3. Structural Limits, Trade-Offs & Bottlenecks"
        section4_title = "## 4. Falsification Boundaries & Open Questions"
    else:
        title_header = f"# Executive Research & Decision Memo: {draft.company_name}"
        status_line = f"**Conclusion / Recommendation**: `{draft.recommendation.value}`"
        section1_title = "## 1. Executive Thesis (Answer-First)"
        section2_title = "## 2. Supporting Strategic / Empirical Pillars"
        section3_title = "## 3. Structural Risks & Pre-Mortem Failure Modes"
        section4_title = "## 4. What Would Change My Mind (Falsification Criteria)"

    lines = [
        title_header,
        "",
        status_line,
        "",
        section1_title,
        "",
        draft.executive_thesis,
        "",
        section2_title,
        "",
        f"### Pillar 1: {draft.pillar_1.headline}",
        "",
        draft.pillar_1.argument,
        "",
        f"*Citations: {', '.join(f'[{cid}]' for cid in draft.pillar_1.cited_claim_ids)}*",
        "",
        f"### Pillar 2: {draft.pillar_2.headline}",
        "",
        draft.pillar_2.argument,
        "",
        f"*Citations: {', '.join(f'[{cid}]' for cid in draft.pillar_2.cited_claim_ids)}*",
        "",
        f"### Pillar 3: {draft.pillar_3.headline}",
        "",
        draft.pillar_3.argument,
        "",
        f"*Citations: {', '.join(f'[{cid}]' for cid in draft.pillar_3.cited_claim_ids)}*",
        "",
        section3_title,
        "",
    ]
    for risk in draft.key_risks:
        lines.append(f"- {risk}")
        lines.append("")

    lines.append(section4_title)
    lines.append("")
    for trigger in draft.what_would_change_my_mind:
        lines.append(f"- {trigger}")
        lines.append("")

    return "\n".join(lines).strip()
