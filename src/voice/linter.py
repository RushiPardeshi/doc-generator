"""Deterministic Anti-Slop Linter for investment memos."""

import re
from typing import List
from pydantic import BaseModel, Field

from src.voice.banned_patterns import (
    COMPILED_BANNED_RULES,
    EM_DASH_PATTERN,
    RULE_OF_THREE_PATTERN,
)
from src.voice.traceability import extract_normalized_tokens


class LintViolation(BaseModel):
    """An identified stylistic or rhetorical violation."""
    line_number: int
    matched_text: str
    rule_description: str


class LintResult(BaseModel):
    """Comprehensive analysis produced by the Anti-Slop Linter."""
    violations: List[LintViolation] = Field(default_factory=list)
    em_dash_count: int = 0
    rule_of_three_count: int = 0
    word_count: int = 0
    sentence_count: int = 0
    metric_density_per_100_words: float = 0.0
    slop_score: float = Field(
        description="Calculated AI slop score from 0.0 (clean analyst prose) to 100.0 (heavily synthetic)"
    )
    is_acceptable: bool = Field(
        description="True if zero banned phrases and acceptable structural counts"
    )


def lint_memo(text: str) -> LintResult:
    """Scan investment memo text for AI tells, banned clichés, and structural patterns."""
    lines = text.splitlines()
    violations: List[LintViolation] = []

    total_words = len(re.findall(r"\b\w+\b", text))
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    sentence_count = max(1, len(sentences))

    # 1. Check line-by-line for banned phrases
    for line_idx, line in enumerate(lines, start=1):
        for pattern_str, (compiled_re, explanation) in COMPILED_BANNED_RULES.items():
            for match in compiled_re.finditer(line):
                violations.append(
                    LintViolation(
                        line_number=line_idx,
                        matched_text=match.group(0),
                        rule_description=explanation,
                    )
                )

    # 2. Check em-dash count
    em_dashes = EM_DASH_PATTERN.findall(text)
    em_dash_count = len(em_dashes)
    # Threshold: more than 1 em-dash per 500 words is considered AI clutter
    max_allowed_em_dashes = max(1, total_words // 500)
    if em_dash_count > max_allowed_em_dashes:
        violations.append(
            LintViolation(
                line_number=0,
                matched_text=f"{em_dash_count} em-dashes found in {total_words} words",
                rule_description=f"Em-dash overuse: found {em_dash_count}, threshold is {max_allowed_em_dashes}. Replace with periods or parentheses.",
            )
        )

    # 3. Check rule-of-three triplets
    rule_of_three_matches = RULE_OF_THREE_PATTERN.findall(text)
    rule_of_three_count = len(rule_of_three_matches)
    for m in rule_of_three_matches:
        triplet_str = f"{m[0]}, {m[1]}, and {m[2]}"
        violations.append(
            LintViolation(
                line_number=0,
                matched_text=triplet_str,
                rule_description="Symmetrical rule-of-three triplet detected. Rephrase with direct factual claims.",
            )
        )

    # 4. Metric Density Calculation
    metric_tokens = extract_normalized_tokens(text)
    metric_density = (len(metric_tokens) / max(1, total_words)) * 100.0

    # 5. Compute Composite Slop Score (0 - 100)
    # Penalty components:
    # - Banned phrase violations: 15 points each
    # - Rule-of-three instances: 8 points each
    # - Excessive em-dashes: 10 points
    # - Low metric density (< 1.5%): +15 points penalty
    score = 0.0
    score += len([v for v in violations if "Banned" in v.rule_description or "Correlative" in v.rule_description]) * 15.0
    score += rule_of_three_count * 8.0
    if em_dash_count > max_allowed_em_dashes:
        score += 10.0 + (em_dash_count - max_allowed_em_dashes) * 5.0

    if metric_density < 1.0:
        score += 15.0
    elif metric_density > 3.0:
        score = max(0.0, score - 5.0)

    score = min(100.0, max(0.0, score))
    is_acceptable = (score < 15.0) and (len(violations) == 0)

    return LintResult(
        violations=violations,
        em_dash_count=em_dash_count,
        rule_of_three_count=rule_of_three_count,
        word_count=total_words,
        sentence_count=sentence_count,
        metric_density_per_100_words=round(metric_density, 2),
        slop_score=round(score, 1),
        is_acceptable=is_acceptable,
    )
