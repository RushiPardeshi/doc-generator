"""Unit tests for Numerical Traceability Guard."""

import pytest
from src.reasoning.claims import GroundedClaim, ClaimType
from src.voice.traceability import verify_numerical_traceability


@pytest.fixture
def sample_claims():
    return [
        GroundedClaim(
            id="C1",
            claim_type=ClaimType.FACT,
            statement="Revenue for H1 2019 was $153.3 million, up 79% YoY.",
            source_quote="Revenue for the six months ended June 30, 2019 was $153.3 million, up 79%.",
            metric_or_data="$153.3 million",
        ),
        GroundedClaim(
            id="C2",
            claim_type=ClaimType.FACT,
            statement="Apex maintains a 146% net retention rate.",
            source_quote="Dollar-based net retention rate was 146% as of June 30, 2019.",
            metric_or_data="146%",
        ),
        GroundedClaim(
            id="C3",
            claim_type=ClaimType.FACT,
            statement="Enterprise customers reached 590, paying over $100,000 ARR.",
            source_quote="Customers with ARR of $100,000 or more reached 590.",
            metric_or_data="590",
        ),
    ]


def test_traceability_passes_with_verified_metrics(sample_claims):
    memo = """
    # Investment Memo: Apex Systems
    **Recommendation**: BUY
    Apex generated $153.3 million in revenue in H1 2019, growing at 79%.
    The business exhibits a 146% net retention rate driven by 590 enterprise customers paying over $100,000.
    """
    report = verify_numerical_traceability(memo, sample_claims)
    assert report.is_valid is True
    assert len(report.untraced_metrics) == 0


def test_traceability_fails_with_invented_metrics(sample_claims):
    memo = """
    # Investment Memo: Apex Systems
    **Recommendation**: BUY
    Apex generated $153.3 million in revenue and will easily reach $850 million by 2022.
    Furthermore, its gross margin of 92% is superior to peers.
    """
    report = verify_numerical_traceability(memo, sample_claims)
    assert report.is_valid is False
    assert any("850" in u for u in report.untraced_metrics)
    assert any("92%" in u or "92" in u for u in report.untraced_metrics)
    assert "Hard Traceability Failure" in report.error_message
