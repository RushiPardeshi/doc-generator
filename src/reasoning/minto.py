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
    """Investment memo structured strictly according to Barbara Minto's Pyramid Principle."""
    company_name: str = Field(description="Name of the target company")
    recommendation: ThesisStance = Field(description="BUY, CONDITIONAL, or PASS")
    executive_thesis: str = Field(
        description="Paragraph 1 Answer-First core thesis and investment recommendation. Zero throat-clearing."
    )
    pillar_1: MintoPillar = Field(description="First supporting structural pillar")
    pillar_2: MintoPillar = Field(description="Second supporting structural pillar")
    pillar_3: MintoPillar = Field(description="Third supporting structural pillar")
    key_risks: List[str] = Field(
        description="Top 3 unvarnished fatal risks or bear-case failure modes from the pre-mortem"
    )
    what_would_change_my_mind: List[str] = Field(
        description="2-3 explicit falsification triggers derived directly from verified claim metrics"
    )


MINTO_SYNTHESIZER_SYSTEM = """You are an elite investment partner drafting an Investment Committee Memo.
You write according to Barbara Minto's Pyramid Principle: ANSWER-FIRST, followed by exactly 3 supporting pillars, unvarnished risks, and falsification criteria.

CRITICAL INVARIANTS:
1. ANSWER-FIRST: Paragraph 1 is the investment decision (BUY, CONDITIONAL, or PASS) and the central thesis. Do NOT start with corporate history or throat-clearing.
2. CITATION DISCIPLINE: Every single supporting pillar MUST cite relevant Claim IDs (e.g. [C1], [C5]) and utilize only the verified metrics provided in those claims.
3. ZERO INVENTED NUMBERS: Every number, dollar figure, and percentage you write MUST originate from the cited claims. Never fabricate benchmark metrics or estimates.
4. FALSIFICATION TRIGGERS: 'What Would Change My Mind' must define quantifiable triggers anchored to the claims (e.g., 'If Net Expansion Rate drops from 146% [C7] below 120%', 'If AWS gross margin pressure drives gross margins from 76.1% [C3] below 68%').
5. PASS HANDLING: If the recommendation is PASS, the 3 pillars must detail why the asset is structurally uninvestable or fatally vulnerable to the pre-mortem failure mode.
"""


def synthesize_minto_draft(
    company_name: str,
    stance: ThesisStance,
    selected_thesis: Optional[CandidateThesis],
    debate_result: DebateArbitrationResult,
    claims: List[GroundedClaim],
    provider: LLMProvider,
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
        thesis_info = "All candidate theses failed the adversarial pre-mortem. Synthesize an unvarnished PASS / AVOID memo.\n"

    premortem_summary = debate_result.arbitration_summary
    fatal_flaws = []
    falsification_hints = []
    for attack in debate_result.attacks:
        fatal_flaws.extend(attack.fatal_flaws)
        falsification_hints.extend(attack.falsification_triggers)

    prompt = f"""Draft a Minto Pyramid Investment Memo for {company_name}.

DECISION: {stance.value}
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


def format_minto_to_markdown(draft: MintoDraft) -> str:
    """Format a MintoDraft object into clean, human-readable markdown prose."""
    lines = [
        f"# Investment Memo: {draft.company_name}",
        f"**Recommendation**: `{draft.recommendation.value}`",
        "",
        "## 1. Executive Thesis (Answer-First)",
        draft.executive_thesis,
        "",
        "## 2. Supporting Investment Pillars",
        f"### Pillar 1: {draft.pillar_1.headline}",
        draft.pillar_1.argument,
        f"*Citations: {', '.join(f'[{cid}]' for cid in draft.pillar_1.cited_claim_ids)}*",
        "",
        f"### Pillar 2: {draft.pillar_2.headline}",
        draft.pillar_2.argument,
        f"*Citations: {', '.join(f'[{cid}]' for cid in draft.pillar_2.cited_claim_ids)}*",
        "",
        f"### Pillar 3: {draft.pillar_3.headline}",
        draft.pillar_3.argument,
        f"*Citations: {', '.join(f'[{cid}]' for cid in draft.pillar_3.cited_claim_ids)}*",
        "",
        "## 3. Structural Risks & Pre-Mortem Failure Modes",
    ]
    for risk in draft.key_risks:
        lines.append(f"- {risk}")

    lines.append("")
    lines.append("## 4. What Would Change My Mind (Falsification Criteria)")
    for trigger in draft.what_would_change_my_mind:
        lines.append(f"- {trigger}")

    return "\n".join(lines)
