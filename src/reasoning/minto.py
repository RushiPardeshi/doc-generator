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


MINTO_SYNTHESIZER_SYSTEM = """You are an elite research director and analytical decision-maker drafting an Executive Research & Decision Memo.
You write according to Barbara Minto's Pyramid Principle: ANSWER-FIRST, followed by exactly 3 supporting pillars, unvarnished structural risks, and falsification criteria.

CRITICAL INVARIANTS:
1. ANSWER-FIRST: Paragraph 1 is the core conclusion/decision (RECOMMEND/BUY, CONDITIONAL, or REJECT/PASS) and the central thesis. Do NOT start with historical throat-clearing or summary padding.
2. CITATION DISCIPLINE: Every single supporting pillar MUST cite relevant Claim IDs (e.g. [C1], [C5]) and utilize only the verified metrics and empirical evidence provided in those claims.
3. ZERO INVENTED NUMBERS: Every measurement, number, percentage, and metric you write MUST originate from the cited claims. Never fabricate benchmark metrics or estimates.
4. FALSIFICATION TRIGGERS: 'What Would Change My Mind' must define quantifiable triggers anchored to the claims (e.g., 'If metric X degrades from Y below Z [C#]').
5. REJECT/PASS HANDLING: If the conclusion is REJECT or PASS, the 3 pillars must detail why the subject/hypothesis is structurally unviable or fatally vulnerable to the pre-mortem failure mode.
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
        thesis_info = "All candidate theses failed the adversarial pre-mortem. Synthesize an unvarnished REJECT / PASS memo.\n"

    premortem_summary = debate_result.arbitration_summary
    fatal_flaws = []
    falsification_hints = []
    for attack in debate_result.attacks:
        fatal_flaws.extend(attack.fatal_flaws)
        falsification_hints.extend(attack.falsification_triggers)

    prompt = f"""Draft a Minto Pyramid Research & Decision Memo for {company_name}.

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


def format_minto_to_markdown(draft: MintoDraft) -> str:
    """Format a MintoDraft object into clean, human-readable markdown prose."""
    lines = [
        f"# Executive Research & Decision Memo: {draft.company_name}",
        f"**Conclusion / Recommendation**: `{draft.recommendation.value}`",
        "",
        "## 1. Executive Thesis (Answer-First)",
        draft.executive_thesis,
        "",
        "## 2. Supporting Strategic / Empirical Pillars",
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
