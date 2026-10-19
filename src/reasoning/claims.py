"""Grounded Claim Extraction with verbatim string match verification."""

import re
from enum import Enum
from typing import Optional, List, Tuple, Dict, Any
from pydantic import BaseModel, Field

from src.llm.base import LLMProvider


class ClaimType(str, Enum):
    """Categorization of extracted claims."""
    FACT = "fact"          # Audited numbers, historical events, filing disclosures
    ESTIMATE = "estimate"  # Forward projections, TAM calculations, industry estimates
    OPINION = "opinion"    # Management commentary, qualitative claims, perceived moats


class GroundedClaim(BaseModel):
    """An atomic, cited claim extracted from research text."""
    id: str = Field(description="Unique identifier, e.g. C1, C2, C3")
    claim_type: ClaimType = Field(description="Type: fact, estimate, or opinion")
    statement: str = Field(description="Crisp, atomic assertion of the claim")
    source_quote: str = Field(description="VERBATIM exact substring from the source dossier")
    metric_or_data: Optional[str] = Field(
        default=None,
        description="Exact metric, percentage, or currency figure if present, e.g. '$153.3 million', '146%'"
    )
    entity_names: List[str] = Field(
        default_factory=list,
        description="Named entities mentioned in this claim, e.g. ['AWS', 'Splunk']"
    )


class ClaimsExtractionResult(BaseModel):
    """Container schema for structured LLM claim extraction."""
    claims: List[GroundedClaim] = Field(
        description="Comprehensive list of atomic claims extracted from the text"
    )


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace and newlines for robust substring matching."""
    return re.sub(r"\s+", " ", text).strip()


def verify_and_filter_claims(
    claims: List[GroundedClaim],
    dossier_text: str,
) -> Tuple[List[GroundedClaim], List[Dict[str, Any]]]:
    """
    Hard Invariant: Verifies that each claim's source_quote exists verbatim in dossier_text.
    
    Returns:
        (verified_claims, rejected_claims)
    """
    normalized_dossier = normalize_whitespace(dossier_text)
    verified: List[GroundedClaim] = []
    rejected: List[Dict[str, Any]] = []

    for claim in claims:
        norm_quote = normalize_whitespace(claim.source_quote)
        if not norm_quote:
            rejected.append({"claim_id": claim.id, "reason": "Empty source quote"})
            continue

        if norm_quote in normalized_dossier:
            verified.append(claim)
        else:
            rejected.append({
                "claim_id": claim.id,
                "reason": "Source quote does not exist verbatim in source text",
                "attempted_quote": claim.source_quote,
            })

    return verified, rejected


CLAIM_EXTRACTION_SYSTEM = """You are an exacting forensic research analyst at a top-tier investment fund.
Your task is to decompose unstructured corporate research documents into atomic, verifiable claims.

CRITICAL INVARIANTS:
1. Every claim MUST include a `source_quote` that is an EXACT, VERBATIM substring of the input text. Do not paraphrase, truncate, or alter punctuation in the quote. If a quote is not found verbatim, the claim will be rejected.
2. Label each claim accurately:
   - 'fact': Audited financial metrics, historical dates, filed customer figures, reported events.
   - 'estimate': Growth estimates, market size projections, forward payback periods.
   - 'opinion': Management commentary, subjective claims about moats, culture, or strategy.
3. Extract ALL key metrics (revenues, growth rates, margins, customer counts, retention rates, payback periods) as distinct claims.
4. Keep the `statement` atomic: one fact or assertion per claim.
"""


def extract_claims(
    dossier_text: str,
    provider: LLMProvider,
) -> Tuple[List[GroundedClaim], List[Dict[str, Any]]]:
    """
    Extract claims from dossier_text and enforce the verbatim string match invariant.
    """
    prompt = f"""Decompose the following investment research dossier into atomic, grounded claims.
Extract at least 15 to 25 comprehensive claims covering financials, product adoption, unit economics, customer concentration, and competitive risks.

DOSSIER CONTENT:
\"\"\"
{dossier_text}
\"\"\"
"""
    result = provider.complete_structured(
        prompt=prompt,
        schema=ClaimsExtractionResult,
        system_instruction=CLAIM_EXTRACTION_SYSTEM,
        temperature=0.1,
    )

    verified_claims, rejected_claims = verify_and_filter_claims(result.claims, dossier_text)
    return verified_claims, rejected_claims
