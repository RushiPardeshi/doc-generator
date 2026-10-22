"""Numerical and Entity Traceability Guard: Prevents hallucinated numbers in investment memos."""

import re
from typing import List, Set, Tuple, Optional
from pydantic import BaseModel, Field

from src.reasoning.claims import GroundedClaim


class TraceabilityReport(BaseModel):
    """Result of verifying that all metrics in a memo originate from verified claims."""
    is_valid: bool
    total_metrics_found: int
    verified_metrics: List[str]
    untraced_metrics: List[str]
    error_message: Optional[str] = None


# Pattern targeting financial figures, scientific/engineering metrics, percentages, multipliers, and multi-digit counts
METRIC_PATTERN = re.compile(
    r"""
    (?:[\$€£¥]\s*\d+(?:\.\d+)?(?:\s*(?:billion|million|trillion|B|M|K|k))?) | # $153.3M, €10.9 million
    (?:\d+(?:\.\d+)?\s*(?:%|pp|percent)\b) |                                    # 79%, 146%, 76.1%, 5 pp
    (?:\d+(?:\.\d+)?\s*x\b) |                                                   # 4.5x, 10x, 2x
    (?:\d+(?:\.\d+)?\s*(?:ms|µs|ns|seconds?|sec|minutes?|mins?|hours?|days?|weeks?|months?|years?|quarters?)\b) | # 120ms, 3 seconds, 12 months
    (?:\d+(?:\.\d+)?\s*(?:gbps|mbps|kbps|tb|gb|mb|kb|req/s|ops/s|qps|flops|tflops|hz|ghz|mhz)\b) |                 # 10 Gbps, 500 req/s, 2.4 GHz
    (?:\b\d{1,3}(?:,\d{3})+\b)                                                  # 8,800, 100,000
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Common structural or benign numbers to exclude from strict financial traceability
STRUCTURAL_NUMBERS = {
    "1", "2", "3", "4", "5", "6", "7", "8", "9", "10",
    "1st", "2nd", "3rd", "first", "second", "third",
    "2012", "2017", "2018", "2019", "2020", "2021", "2022", "2023", "2024", "2025", "2026",
    "30", # June 30
}


def extract_normalized_tokens(text: str) -> Set[str]:
    """Extract and normalize all numeric and metric tokens from text."""
    normalized: Set[str] = set()

    # 1. Match full metric phrases ($153.3 million, 79%, 146%, 12 months, etc.)
    for m in METRIC_PATTERN.findall(text):
        cleaned = re.sub(r"\s+", " ", m.strip().lower()).replace(",", "")
        normalized.add(cleaned)

    # 2. Extract numeric amounts without splitting comma-formatted numbers (e.g. 100,000 -> 100000)
    comma_numbers = re.findall(r"\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b", text)
    for num in comma_numbers:
        cleaned = num.replace(",", "")
        if cleaned not in STRUCTURAL_NUMBERS:
            normalized.add(cleaned)

    return normalized


def build_allowed_metrics_corpus(claims: List[GroundedClaim]) -> Set[str]:
    """Extract all allowed numeric and metric tokens from verified claims."""
    allowed: Set[str] = set()
    for claim in claims:
        # From statement
        allowed.update(extract_normalized_tokens(claim.statement))
        # From verbatim source quote
        allowed.update(extract_normalized_tokens(claim.source_quote))
        # From metric_or_data if provided
        if claim.metric_or_data:
            allowed.update(extract_normalized_tokens(claim.metric_or_data))

    return allowed


def verify_numerical_traceability(
    memo_text: str,
    claims: List[GroundedClaim],
) -> TraceabilityReport:
    """
    Hard Invariant: Scans memo_text for all financial metrics and quantities.
    Every single metric MUST exist in the claims corpus.
    Any untraced metric causes a hard failure.
    """
    memo_tokens = extract_normalized_tokens(memo_text)
    allowed_corpus = build_allowed_metrics_corpus(claims)

    verified: List[str] = []
    untraced: List[str] = []

    for token in memo_tokens:
        # Check direct membership
        if token in allowed_corpus:
            verified.append(token)
            continue

        # Check if the numeric portion is contained in any allowed token (e.g. 153.3 in 153.3m)
        num_match = re.search(r"\d+(?:\.\d+)?", token)
        if num_match:
            raw_num = num_match.group(0)
            if any(raw_num in allowed_token for allowed_token in allowed_corpus):
                verified.append(token)
                continue

        # Check if token is benign or structural
        if token in STRUCTURAL_NUMBERS:
            continue

        untraced.append(token)

    is_valid = len(untraced) == 0
    error_msg = None
    if not is_valid:
        error_msg = (
            f"Hard Traceability Failure: Detected {len(untraced)} invented or ungrounded metrics in final memo: "
            f"{', '.join(untraced)}. Every metric must trace directly to a verified claim."
        )

    return TraceabilityReport(
        is_valid=is_valid,
        total_metrics_found=len(memo_tokens),
        verified_metrics=verified,
        untraced_metrics=untraced,
        error_message=error_msg,
    )
