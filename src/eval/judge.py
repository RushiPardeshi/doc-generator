"""Cross-Model Comparative Evaluation using an independent LLM Judge."""

import random
from typing import Literal, List, Tuple
from pydantic import BaseModel, Field

from src.llm.base import LLMProvider


class DimensionScore(BaseModel):
    """Evaluation score for a single rubric dimension."""
    score: float = Field(ge=1.0, le=5.0, description="Rating from 1.0 (poor/generic) to 5.0 (exceptional)")
    critique: str = Field(description="Exacting critique explaining the score")


class MemoScorecard(BaseModel):
    """Rubric scorecard for one evaluated memo."""
    falsifiability: DimensionScore = Field(
        description="Falsifiability: Is the thesis testable? Are failure triggers concrete and quantitative?"
    )
    evidence_grounding: DimensionScore = Field(
        description="Evidence Grounding: Are claims supported by verified metrics vs hand-waving?"
    )
    premortem_realism: DimensionScore = Field(
        description="Pre-Mortem Realism: Does the memo identify how it can lose money or just list generic boilerplate risks?"
    )
    prose_slop_absence: DimensionScore = Field(
        description="Prose Conviction & Slop Absence: Is the prose natural, dense, and unhedged vs synthetic AI padding?"
    )
    overall_score: float = Field(description="Weighted overall score out of 5.0")
    one_line_verdict: str = Field(description="One-line executive summary of quality")


class ComparativeEvaluationResult(BaseModel):
    """Structured verdict from the independent judge comparing two blind memos."""
    memo_a_scorecard: MemoScorecard
    memo_b_scorecard: MemoScorecard
    preferred_memo: Literal["A", "B", "TIE"]
    key_differentiators: List[str]
    verdict_explanation: str


JUDGE_SYSTEM = """You are an independent Senior Partner at a multi-billion dollar investment fund.
Your task is to conduct a BLIND, rigorous comparative evaluation of two investment committee memos.

EVALUATION RUBRIC (1.0 to 5.0 scale):
1. Falsifiability & Thesis Clarity (1-5):
   - 1.0: Vague, non-committal summary ('Apex is well-positioned in a growing market').
   - 5.0: Highly falsifiable answer-first thesis with quantitative invalidation triggers.
2. Evidence Grounding & Linkage (1-5):
   - 1.0: Unsubstantiated claims, qualitative fluff, or missing citations.
   - 5.0: Every claim is mathematically linked to specific filing metrics (NRR, payback, margins, revenue).
3. Pre-Mortem Realism (1-5):
   - 1.0: Generic boilerplate risks ('macro risks', 'cybersecurity threats').
   - 5.0: Concrete structural failure modes (AWS bundling, unit economics deterioration, cloud decelerations).
4. Prose Conviction & Slop Absence (1-5):
   - 1.0: Classic AI slop ('not only X but also Y', 'testament to', 'evolving landscape', em-dash spam).
   - 5.0: Understated, clean analyst prose; zero throat-clearing; high empirical density.

Be ruthlessly objective. Do NOT reward length or empty rhetorical flourishes.
"""


def evaluate_memos_blind(
    baseline_memo: str,
    pipeline_memo: str,
    judge_provider: LLMProvider,
) -> Tuple[ComparativeEvaluationResult, str, str]:
    """
    Perform a blind comparative evaluation between Baseline and Pipeline memos.
    Randomly assigns labels 'Memo A' and 'Memo B' to eliminate positional bias.
    
    Returns:
        (judge_result, label_for_baseline, label_for_pipeline)
    """
    is_baseline_a = random.choice([True, False])
    memo_a = baseline_memo if is_baseline_a else pipeline_memo
    memo_b = pipeline_memo if is_baseline_a else baseline_memo

    from src.llm.tracker import token_tracker
    token_tracker.set_current_stage("3/3 Independent Blind Judge")

    prompt = f"""Evaluate the two blind investment memos below according to the rubric.

============================== MEMO A ==============================
{memo_a}

============================== MEMO B ==============================
{memo_b}
"""

    result = judge_provider.complete_structured(
        prompt=prompt,
        schema=ComparativeEvaluationResult,
        system_instruction=JUDGE_SYSTEM,
        temperature=0.1,
    )

    label_baseline = "A" if is_baseline_a else "B"
    label_pipeline = "B" if is_baseline_a else "A"

    return result, label_baseline, label_pipeline
