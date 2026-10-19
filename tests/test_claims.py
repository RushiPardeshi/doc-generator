"""Unit tests for GroundedClaim extraction and verbatim string match invariant."""

import pytest
from src.reasoning.claims import (
    GroundedClaim,
    ClaimType,
    verify_and_filter_claims,
    normalize_whitespace,
)

SAMPLE_DOSSIER = """
Revenue for the six months ended June 30, 2019 was $153.3 million, up 79% from $85.4 million
for the six months ended June 30, 2018. Gross margin was 76.1%.
Apex generated positive operating cash flow of $10.9 million.
"""


def test_normalize_whitespace():
    raw = "Revenue   for the  \n six months\nended"
    assert normalize_whitespace(raw) == "Revenue for the six months ended"


def test_verbatim_quote_acceptance():
    claims = [
        GroundedClaim(
            id="C1",
            claim_type=ClaimType.FACT,
            statement="Apex grew H1 2019 revenue 79% YoY to $153.3M",
            source_quote="Revenue for the six months ended June 30, 2019 was $153.3 million, up 79% from $85.4 million for the six months ended June 30, 2018.",
            metric_or_data="$153.3 million",
            entity_names=["Apex"],
        ),
        GroundedClaim(
            id="C2",
            claim_type=ClaimType.FACT,
            statement="Gross margin was 76.1%",
            source_quote="Gross margin was 76.1%.",
            metric_or_data="76.1%",
            entity_names=[],
        ),
    ]

    verified, rejected = verify_and_filter_claims(claims, SAMPLE_DOSSIER)
    assert len(verified) == 2
    assert len(rejected) == 0
    assert verified[0].id == "C1"
    assert verified[1].id == "C2"


def test_fabricated_quote_rejection():
    claims = [
        GroundedClaim(
            id="C1",
            claim_type=ClaimType.FACT,
            statement="Invented ARR claim",
            source_quote="Apex achieved $500 million in ARR by end of 2019.",
            metric_or_data="$500 million",
            entity_names=["Apex"],
        ),
        GroundedClaim(
            id="C2",
            claim_type=ClaimType.FACT,
            statement="Valid cash flow claim",
            source_quote="Apex generated positive operating cash flow of $10.9 million.",
            metric_or_data="$10.9 million",
            entity_names=["Apex"],
        ),
    ]

    verified, rejected = verify_and_filter_claims(claims, SAMPLE_DOSSIER)
    assert len(verified) == 1
    assert verified[0].id == "C2"
    assert len(rejected) == 1
    assert rejected[0]["claim_id"] == "C1"
    assert "does not exist verbatim" in rejected[0]["reason"]
