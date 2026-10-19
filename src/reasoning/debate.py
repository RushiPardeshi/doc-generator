"""Candidate Thesis Generation with Bull/Conditional/Pass stances and Adversarial Pre-Mortem Debate."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.reasoning.claims import GroundedClaim
from src.llm.base import LLMProvider


class ThesisStance(str, Enum):
    """Investment stance of a proposed thesis."""
    BUY = "BUY"                    # Strong conviction investment thesis
    CONDITIONAL = "CONDITIONAL"    # Viable only at strict valuation or specific operational covenants
    PASS = "PASS"                  # Structural flaw, fatal risk, or uninvestable unit economics


class CandidateThesis(BaseModel):
    """A distinct, testable investment thesis."""
    id: str = Field(description="Identifier: T1, T2, T3")
    stance: ThesisStance = Field(description="BUY, CONDITIONAL, or PASS")
    headline: str = Field(description="One-sentence high-conviction thesis statement")
    core_mechanism: str = Field(
        description="The structural economic mechanism: flywheel, pricing power, commoditization, or duration mismatch"
    )
    supporting_claim_ids: List[str] = Field(
        description="IDs of extracted claims that substantiate this thesis (e.g. ['C1', 'C5'])"
    )
    primary_vulnerability: str = Field(
        description="The most dangerous unstated assumption or risk embedded in this thesis"
    )


class ThesesGenerationResult(BaseModel):
    """Collection of 3 orthogonal candidate theses."""
    theses: List[CandidateThesis] = Field(
        description="Exactly 3 diverse candidate theses: at least one BUY, one CONDITIONAL, and one PASS/AVOID"
    )


class PreMortemAttack(BaseModel):
    """Adversarial stress-test attacking a single candidate thesis."""
    thesis_id: str = Field(description="ID of the attacked thesis: T1, T2, or T3")
    fatal_failure_narrative: str = Field(
        description="3-year fatal failure scenario: assume this investment destroyed capital; explain precisely how"
    )
    survived: bool = Field(
        description="True if the core thesis remains viable despite the attack; False if fatally flawed"
    )
    survival_score: float = Field(
        description="Survival rating from 1.0 (dead on arrival) to 10.0 (antifragile / robustly defended)"
    )
    fatal_flaws: List[str] = Field(
        description="Concrete structural flaws or broken assumptions exposed by the attack"
    )
    falsification_triggers: List[str] = Field(
        description="Quantitative conditions derived strictly from cited claims that would immediately prove this thesis wrong"
    )


class DebateArbitrationResult(BaseModel):
    """The outcome of the adversarial pre-mortem debate and thesis selection."""
    attacks: List[PreMortemAttack] = Field(description="Pre-mortem attacks on all 3 candidate theses")
    selected_thesis_id: Optional[str] = Field(
        description="The surviving thesis selected for memo synthesis, or None if all failed"
    )
    final_stance: ThesisStance = Field(
        description="The synthesized stance: BUY, CONDITIONAL, or PASS"
    )
    arbitration_summary: str = Field(
        description="Rigorous rationale explaining which thesis survived or why all theses were rejected"
    )


THESIS_GENERATOR_SYSTEM = """You are a senior investment partner at a top-tier venture / growth equity fund.
Your job is to formulate 3 ORTHOGONAL, high-conviction candidate theses from the provided factual claims.

RULES:
1. Do NOT provide 3 generic variations of the same bull case.
2. You MUST propose exactly:
   - One high-conviction BUY thesis (e.g. platform expansion, multi-product flywheel, structural expansion)
   - One CONDITIONAL thesis (viable only if margin of safety or specific unit economics hold)
   - One explicit PASS / AVOID thesis (e.g. public cloud native bundling commoditization, margin vulnerability to AWS hosting, or customer concentration risks)
3. Every thesis must explicitly cite the `id` of at least 2 supporting claims.
4. The headline must be falsifiable—someone must be able to take the exact opposite side of the trade.
"""

CRITIC_PREMORTEM_SYSTEM = """You are the 'Red Team' / Chief Risk Officer at an investment committee.
Your sole purpose is to destroy the proposed candidate theses through an adversarial PRE-MORTEM (Du et al., 2023).

PRE-MORTEM DIRECTIVE:
\"Assume it is 3 years from today. The fund made this investment and it lost 80% of its capital. It is a catastrophic failure. Exactly how did it fail?\"

RULES:
1. Attack the unstated assumptions: What if cloud hosting costs surge? What if the 146% NRR decelerates? What if AWS/Azure bundle competing tools for free?
2. Score each thesis's survival on a 1.0 to 10.0 scale.
3. If a thesis relies on hand-waving or cannot withstand competitive bundling, mark `survived = False`.
4. Derive concrete `falsification_triggers` tied directly to the claims (e.g. 'If NRR drops from 146% below 115%').
5. If ALL candidate theses are fatally flawed or the PASS thesis exposes an insurmountable structural risk, select `final_stance = 'PASS'`.
"""


def generate_candidate_theses(
    claims: List[GroundedClaim],
    provider: LLMProvider,
) -> List[CandidateThesis]:
    """Propose 3 orthogonal candidate theses (BUY, CONDITIONAL, PASS) based on verified claims."""
    claims_summary = "\n".join(
        f"[{c.id}] ({c.claim_type.value}): {c.statement}" + (f" | Metric: {c.metric_or_data}" if c.metric_or_data else "")
        for c in claims
    )

    prompt = f"""Based on the following verified claims, generate 3 orthogonal candidate theses (1 BUY, 1 CONDITIONAL, 1 PASS).

VERIFIED CLAIMS:
{claims_summary}
"""
    result = provider.complete_structured(
        prompt=prompt,
        schema=ThesesGenerationResult,
        system_instruction=THESIS_GENERATOR_SYSTEM,
        temperature=0.3,
    )
    return result.theses


def run_premortem_debate(
    theses: List[CandidateThesis],
    claims: List[GroundedClaim],
    provider: LLMProvider,
) -> DebateArbitrationResult:
    """Run adversarial pre-mortem attacks on all 3 candidate theses and select the survivor."""
    claims_map = {c.id: c for c in claims}
    
    theses_text = "\n\n".join(
        f"Thesis {t.id} [{t.stance.value}]:\n"
        f"Headline: {t.headline}\n"
        f"Core Mechanism: {t.core_mechanism}\n"
        f"Supporting Claims: {', '.join(t.supporting_claim_ids)}\n"
        f"Primary Vulnerability: {t.primary_vulnerability}"
        for t in theses
    )

    prompt = f"""Conduct an adversarial pre-mortem attack on each of the 3 candidate theses below.

CANDIDATE THESES:
{theses_text}

Deliver:
1. A ruthless fatal failure narrative for each thesis.
2. A survival score (1.0 to 10.0) and whether it survived.
3. Concrete falsification triggers based on the claims.
4. An overall arbitration decision. If the PASS thesis is the most structurally sound or all BUY/CONDITIONAL theses are destroyed, select final_stance = 'PASS'.
"""
    result = provider.complete_structured(
        prompt=prompt,
        schema=DebateArbitrationResult,
        system_instruction=CRITIC_PREMORTEM_SYSTEM,
        temperature=0.2,
    )
    return result
