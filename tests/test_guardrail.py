"""Tests for category guardrails and recommendation restrictions."""

from src.routing.models import QueryCategory
from src.templates.guardrail import (
    verify_recommendation_guardrail,
    scrub_recommendations_if_present,
)


def test_guardrail_allows_recommendations_for_company():
    memo = "Our recommendation: BUY with a target price of $200. Investors should accumulate."
    is_valid, violations = verify_recommendation_guardrail(memo, QueryCategory.COMPANY)
    assert is_valid is True
    assert len(violations) == 0


def test_guardrail_blocks_recommendations_for_topic():
    bad_output = (
        "In conclusion, we recommend implementing this architecture immediately. "
        "Investors should allocate capital towards this technology."
    )
    is_valid, violations = verify_recommendation_guardrail(bad_output, QueryCategory.TOPIC)
    assert is_valid is False
    assert len(violations) >= 2


def test_guardrail_passes_clean_topic():
    clean_output = (
        "Empirical benchmarks demonstrate 3.4x throughput efficiency. "
        "Theoretical limitations remain unresolved at high noise thresholds."
    )
    is_valid, violations = verify_recommendation_guardrail(clean_output, QueryCategory.TOPIC)
    assert is_valid is True
    assert len(violations) == 0


def test_scrub_recommendations():
    text = "Based on our findings, we recommend adopting the protocol."
    cleaned = scrub_recommendations_if_present(text)
    assert "we recommend" not in cleaned.lower()
