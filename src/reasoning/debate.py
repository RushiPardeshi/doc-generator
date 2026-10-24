"""Candidate Thesis Generation with Bull/Conditional/Pass stances and Adversarial Pre-Mortem Debate."""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from src.reasoning.claims import GroundedClaim
from src.llm.base import LLMProvider


class ThesisStance(str, Enum):
    """Actionable stance of a proposed thesis or conclusion across analytical domains."""
    # Research mode stances:
    VALIDATED = "VALIDATED"          # Strong empirical grounding / Hypothesis supported / Efficacy proven
    CONSTRAINED = "CONSTRAINED"      # Holds within defined operational boundaries / Trade-offs required
    DISCONFIRMED = "DISCONFIRMED"    # Structural failure / Hypothesis unproven / Bottlenecks dominate
    # Investment / Decision mode aliases:
    RECOMMEND = "RECOMMEND"        # Strong conviction positive thesis / Buy / Adopt / Validate
    CONDITIONAL = "CONDITIONAL"    # Viable only with strict caveats, margin of safety, or specific conditions
    REJECT = "REJECT"              # Fatal flaw / Refute / Unviable / Pass / Avoid
    BUY = "BUY"
    PASS = "PASS"


class CandidateThesis(BaseModel):
    """A distinct, testable thesis or conclusion."""
    id: str = Field(description="Identifier: T1, T2, T3")
    stance: ThesisStance = Field(description="RECOMMEND/BUY, CONDITIONAL, or REJECT/PASS")
    headline: str = Field(description="One-sentence high-conviction thesis statement or conclusion")
    core_mechanism: str = Field(
        description="The structural mechanism: causal driver, economic flywheel, technical advantage, or fundamental dynamic"
    )
    supporting_claim_ids: List[str] = Field(
        description="IDs of extracted claims that substantiate this thesis (e.g. ['C1', 'C5'])"
    )
    primary_vulnerability: str = Field(
        description="The most dangerous unstated assumption, risk, or counter-evidence embedded in this thesis"
    )


class ThesesGenerationResult(BaseModel):
    """Collection of 3 orthogonal candidate theses."""
    theses: List[CandidateThesis] = Field(
        description="Exactly 3 diverse candidate theses: at least one RECOMMEND/BUY, one CONDITIONAL, and one REJECT/PASS"
    )


class PreMortemAttack(BaseModel):
    """Adversarial stress-test attacking a single candidate thesis."""
    thesis_id: str = Field(description="ID of the attacked thesis: T1, T2, or T3")
    fatal_failure_narrative: str = Field(
        description="Fatal failure scenario: assume this thesis or recommendation failed catastrophically; explain precisely how"
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
        description="The synthesized stance: RECOMMEND/BUY, CONDITIONAL, or REJECT/PASS"
    )
    arbitration_summary: str = Field(
        description="Rigorous rationale explaining which thesis survived or why all theses were rejected"
    )


THESIS_GENERATOR_SYSTEM = """You are an exacting senior principal researcher and analytical decision-maker.
Your job is to formulate 3 ORTHOGONAL, high-conviction candidate theses or conclusions from the provided factual research claims.

RULES:
1. Do NOT provide 3 generic variations of the same finding.
2. You MUST propose exactly:
   - One high-conviction RECOMMEND / POSITIVE thesis (e.g. core causal mechanism holds, dominant adoption/efficacy, validated hypothesis)
   - One CONDITIONAL thesis (viable only if strict constraints, margin of safety, or specific prerequisites are satisfied)
   - One explicit REJECT / SKEPTICAL / PASS thesis (e.g. structural flaw, fatal bottleneck, unviable trade-off, or disconfirmed hypothesis)
3. Every thesis must explicitly cite the `id` of at least 2 supporting claims.
4. The headline must be falsifiable—someone must be able to take the exact opposite side.
"""

CRITIC_PREMORTEM_SYSTEM = """You are an adversarial 'Red Team' reviewer and Lead Critic.
Your sole purpose is to stress-test and destroy the proposed candidate theses through an adversarial PRE-MORTEM (Du et al., 2023).

PRE-MORTEM DIRECTIVE:
\"Assume time has passed and this recommendation, thesis, or proposed direction failed catastrophically in practice (e.g. system failure in production, capital destruction, unviable unit economics, unvalidated scientific hypotheses, or deployment bottlenecks). Exactly what broken assumption or real-world friction caused the failure?\"

RULES:
1. Attack the unstated assumptions: What if core dependencies fail? What if key metrics decelerate? What if competitive or environmental forces invalidate the model?
2. Score each thesis's survival on a 1.0 to 10.0 scale.
3. If a thesis relies on hand-waving or cannot withstand the failure mode, mark `survived = False`.
4. Derive concrete `falsification_triggers` tied directly to the claims (e.g. 'If metric X degrades from Y below Z').
5. ARBITRATION DISCIPLINE: If the empirical evidence proves the thesis works well within a defined operating envelope (e.g., specific workloads, parameter ranges, or constraints) but fails outside them, select `final_stance = 'CONDITIONAL'` with clear operational constraints. Select `final_stance = 'REJECT'` (or 'PASS') ONLY if the thesis is structurally defective across all viable operating regimes. In `arbitration_summary`, describe practical boundaries and numbers directly; do NOT output meta-language like 'The thesis survives only within these guardrails'.
"""


def generate_candidate_theses(
    claims: List[GroundedClaim],
    provider: LLMProvider,
    mode: str = "research",
) -> List[CandidateThesis]:
    """Propose 3 orthogonal candidate theses based on verified claims."""
    claims_summary = "\n".join(
        f"[{c.id}] ({c.claim_type.value}): {c.statement}" + (f" | Metric: {c.metric_or_data}" if c.metric_or_data else "")
        for c in claims
    )

    if mode == "research":
        prompt = f"""Based on the following verified claims, generate 3 orthogonal candidate research theses:
1. One VALIDATED thesis (the core mechanism is theoretically sound and empirically proven by benchmark data)
2. One CONSTRAINED thesis (valid within a specific operating envelope or parameter range; exhibits clear trade-offs/bottlenecks)
3. One DISCONFIRMED thesis (fundamental structural limitations, scaling collapse, or unviable trade-offs dominate)

Do NOT output corporate 'buy/deploy' investment stances. Use VALIDATED, CONSTRAINED, or DISCONFIRMED.

VERIFIED CLAIMS:
{claims_summary}
"""
    else:
        prompt = f"""Based on the following verified claims, generate 3 orthogonal candidate theses (1 RECOMMEND/BUY, 1 CONDITIONAL, 1 REJECT/PASS).

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
    mode: str = "research",
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

    if mode == "research":
        prompt = f"""Conduct an adversarial pre-mortem critique on each of the 3 candidate research theses below to identify hidden assumptions, edge cases, and real-world bottlenecks.

CANDIDATE THESES:
{theses_text}

Deliver:
1. A rigorous failure/bottleneck narrative for each thesis.
2. A survival score (1.0 to 10.0) and whether the core thesis holds.
3. Concrete falsification triggers based on the claims.
4. An overall arbitration decision selecting the most empirically sound thesis stance (VALIDATED, CONSTRAINED, or DISCONFIRMED). Do NOT force corporate procurement or deploy decisions.
"""
    else:
        prompt = f"""Conduct an adversarial pre-mortem attack on each of the 3 candidate theses below.

CANDIDATE THESES:
{theses_text}

Deliver:
1. A ruthless fatal failure narrative for each thesis.
2. A survival score (1.0 to 10.0) and whether it survived.
3. Concrete falsification triggers based on the claims.
4. An overall arbitration decision. If the REJECT/PASS thesis is the most structurally sound or all positive/conditional theses are destroyed, select final_stance = 'REJECT' (or 'PASS').
"""
    result = provider.complete_structured(
        prompt=prompt,
        schema=DebateArbitrationResult,
        system_instruction=CRITIC_PREMORTEM_SYSTEM,
        temperature=0.2,
    )
    return result
