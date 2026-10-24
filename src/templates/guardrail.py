"""Guardrails enforcing category constraints and recommendation prohibitions."""

import re
from typing import Tuple, List
from src.routing.models import QueryCategory


# Disallowed recommendation patterns for TOPIC, INDUSTRY, and MACRO queries
FORBIDDEN_RECOMMENDATION_PATTERNS = [
    r"\bwe recommend\b",
    r"\bour recommendation\b",
    r"\brecommendation:\b",
    r"\brecommended action\b",
    r"\binvestors should\b",
    r"\byou should invest\b",
    r"\byou should consider buying\b",
    r"\bwe suggest (?:investing|buying|selling|allocating)\b",
    r"\bactionable advice\b",
    r"\baction items:\b",
    r"\bportfolio allocation\b",
    r"\bbuy recommendation\b",
    r"\bsell recommendation\b",
    r"\btarget price\b",
]


def verify_recommendation_guardrail(
    text: str,
    category: QueryCategory,
) -> Tuple[bool, List[str]]:
    """
    Verify that queries categorized as TOPIC, INDUSTRY, or MACRO do NOT contain
    forbidden investment recommendations or suggestions.

    Returns:
        (is_valid, list_of_violations)
    """
    if category == QueryCategory.COMPANY:
        # Recommendations and convictions are explicitly permitted and required for company investment memos
        return True, []

    violations = []
    text_lower = text.lower()
    for pattern in FORBIDDEN_RECOMMENDATION_PATTERNS:
        matches = re.findall(pattern, text_lower)
        if matches:
            violations.append(f"Forbidden recommendation phrase detected: '{matches[0]}'")

    is_valid = len(violations) == 0
    return is_valid, violations


def scrub_recommendations_if_present(text: str) -> str:
    """Utility to clean up minor recommendation leaks if present in research topic output."""
    cleaned = text
    for pattern in FORBIDDEN_RECOMMENDATION_PATTERNS:
        cleaned = re.sub(pattern, "[objective observation noted]", cleaned, flags=re.IGNORECASE)
    return cleaned
