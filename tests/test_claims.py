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


def test_markdown_and_unicode_quote_recovery():
    technical_dossier = """
### 1. Model Overview & Empirical Metrics
The **Local Implicit Image Function (LIIF)** represents an image continuously.
According to researchers, LIIF achieved a “34.2 dB” PSNR on arbitrary-scale super-resolution — outperforming bicubic baselines.
The model executes in $120\\text{ms}$ with zero memory leakage.
"""
    # Simulate quotes where LLM stripped markdown bolding, straight-quoted, or converted dashes
    claims = [
        GroundedClaim(
            id="C1",
            claim_type=ClaimType.FACT,
            statement="LIIF represents an image continuously",
            source_quote="The Local Implicit Image Function (LIIF) represents an image continuously.",
            entity_names=["LIIF"],
        ),
        GroundedClaim(
            id="C2",
            claim_type=ClaimType.FACT,
            statement="LIIF achieved 34.2 dB PSNR",
            source_quote='According to researchers, LIIF achieved a "34.2 dB" PSNR on arbitrary-scale super-resolution - outperforming bicubic baselines.',
            metric_or_data="34.2 dB",
            entity_names=["LIIF"],
        ),
        GroundedClaim(
            id="C3",
            claim_type=ClaimType.FACT,
            statement="Completely fabricated metric on nonexistent dataset",
            source_quote="LIIF scored 99.8% top-1 accuracy on ImageNet zero-shot benchmark.",
            metric_or_data="99.8%",
            entity_names=["LIIF", "ImageNet"],
        ),
    ]

    verified, rejected = verify_and_filter_claims(claims, technical_dossier)

    # C1 and C2 should be recovered and anchored to verbatim slice
    assert len(verified) == 2
    assert verified[0].id == "C1"
    assert verified[1].id == "C2"
    # Ensure recovered quote exists verbatim in raw technical_dossier
    assert verified[0].source_quote in technical_dossier
    assert verified[1].source_quote in technical_dossier

    # Fabricated claim C3 must still be rejected
    assert len(rejected) == 1
    assert rejected[0]["claim_id"] == "C3"

