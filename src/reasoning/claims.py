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
    return re.sub(r"[\s\u00a0\u200b]+", " ", text).strip()


def canonical_clean_text(text: str) -> str:
    """
    Normalize text for semantic comparison:
    - Normalizes smart quotes and unicode dashes.
    - Strips markdown formatting markers (bold, italic, code, math delimiters).
    - Normalizes non-breaking and zero-width spaces.
    """
    t = text
    trans = str.maketrans({
        "“": '"', "”": '"', "‘": "'", "’": "'", "`": "'", "´": "'",
        "—": "-", "–": "-", "−": "-",
    })
    t = t.translate(trans)
    # Strip markdown markers without altering inner text
    t = re.sub(r"\*\*([^*]+)\*\*", r"\1", t)
    t = re.sub(r"\*([^*]+)\*", r"\1", t)
    t = re.sub(r"__([^_]+)__", r"\1", t)
    t = re.sub(r"_([^_]+)_", r"\1", t)
    t = re.sub(r"`([^`]+)`", r"\1", t)
    t = re.sub(r"\$([^$]+)\$", r"\1", t)
    return normalize_whitespace(t)


def _extract_words(text: str) -> List[str]:
    """Extract lowercase alphanumeric tokens for overlap calculation."""
    return [w.lower() for w in re.findall(r"\b[A-Za-z0-9]+\b", text)]


def _recover_verbatim_slice(quote: str, dossier_text: str) -> Optional[str]:
    """
    Attempt to locate and extract the verbatim slice from dossier_text:
    1. Token-level regex match (handles markdown bolding/italics inside the quote).
    2. Sentence alignment with high lexical overlap (>= 85%).
    """
    clean_q = canonical_clean_text(quote)
    words = [re.escape(w) for w in re.findall(r"\w+|[^\w\s]", clean_q) if w.strip()]
    if len(words) >= 3:
        sep = r"[\s\*\_\`\$\"\“\”\‘\’\—\–\-]*"
        pattern = sep.join(words)
        try:
            m = re.search(pattern, dossier_text, flags=re.IGNORECASE)
            if m:
                return m.group(0).strip()
        except re.error:
            pass

    # High-overlap sentence alignment
    sentences = [s.strip() for s in re.split(r"(?<=[.!?\n])\s+", dossier_text) if s.strip()]
    q_words = _extract_words(clean_q)
    if not q_words or len(q_words) < 3:
        return None

    q_set = set(q_words)
    best_match = None
    best_overlap = 0.0

    for s in sentences:
        s_words = _extract_words(canonical_clean_text(s))
        if not s_words:
            continue
        s_set = set(s_words)
        overlap = len(q_set & s_set) / max(len(q_set), 1)
        if overlap > best_overlap:
            best_overlap = overlap
            best_match = s

    if best_overlap >= 0.85 and best_match:
        return best_match

    return None


def verify_and_filter_claims(
    claims: List[GroundedClaim],
    dossier_text: str,
) -> Tuple[List[GroundedClaim], List[Dict[str, Any]]]:
    """
    Hard Invariant with Multi-Tier Verification:
    Tier 1: Direct exact match in normalized dossier.
    Tier 2: Token-level regex match (handles markdown, quotes, dashes) & recovers verbatim slice.
    Tier 3: High-confidence sentence alignment & recovers verbatim slice.
    
    Returns:
        (verified_claims, rejected_claims)
    """
    normalized_dossier = normalize_whitespace(dossier_text)
    clean_dossier = canonical_clean_text(dossier_text)

    verified: List[GroundedClaim] = []
    rejected: List[Dict[str, Any]] = []

    for claim in claims:
        norm_quote = normalize_whitespace(claim.source_quote)
        if not norm_quote:
            rejected.append({"claim_id": claim.id, "reason": "Empty source quote"})
            continue

        # Tier 1: Exact whitespace-normalized substring
        if norm_quote in normalized_dossier:
            verified.append(claim)
            continue

        # Tier 2: Canonical clean match (e.g. smart quotes or stripped markdown)
        clean_quote = canonical_clean_text(claim.source_quote)
        if clean_quote in clean_dossier:
            recovered_slice = _recover_verbatim_slice(claim.source_quote, dossier_text)
            if recovered_slice:
                claim.source_quote = recovered_slice
                verified.append(claim)
                continue

        # Tier 3: Lexical alignment & slice recovery
        recovered_slice = _recover_verbatim_slice(claim.source_quote, dossier_text)
        if recovered_slice:
            claim.source_quote = recovered_slice
            verified.append(claim)
            continue

        # Rejection: truly not found or fabricated
        rejected.append({
            "claim_id": claim.id,
            "reason": "Source quote does not exist verbatim in source text",
            "attempted_quote": claim.source_quote,
        })

    return verified, rejected


CLAIM_EXTRACTION_SYSTEM = """You are an exacting forensic research analyst and lead scientific/technical reviewer.
Your task is to decompose unstructured research documents, technical papers, corporate disclosures, or analytical dossiers into atomic, verifiable claims.

CRITICAL INVARIANTS:
1. Every claim MUST include a `source_quote` that is an EXACT, VERBATIM substring of the input text. Do not paraphrase, truncate, or alter punctuation in the quote. If a quote is not found verbatim, the claim will be rejected.
2. Label each claim accurately:
   - 'fact': Audited financial metrics, measured benchmark results, historical dates, observed outcomes, empirical findings.
   - 'estimate': Forward projections, statistical confidence intervals, TAM/capacity estimates, modeling forecasts.
   - 'opinion': Author/management commentary, subjective claims about moats, culture, architecture advantages, or strategy.
3. Extract ALL key metrics (quantitative measurements, percentages, latency/throughput, error rates, financial figures, customer counts, dates) as distinct claims.
4. Keep the `statement` atomic: one fact, finding, or assertion per claim.
"""


def extract_claims(
    dossier_text: str,
    provider: LLMProvider,
) -> Tuple[List[GroundedClaim], List[Dict[str, Any]]]:
    """
    Extract claims from dossier_text and enforce the verbatim string match invariant.
    """
    prompt = f"""Decompose the following research dossier / document into atomic, grounded claims.
Extract at least 15 to 25 comprehensive claims covering core findings, empirical data, metrics, operational dynamics, methodology, and risks/limitations.

DOCUMENT CONTENT:
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

    # 1-Shot Self-Correction Retry Loop if initial extraction had low yield (< 3 verified claims)
    if len(verified_claims) < 3 and provider:
        retry_prompt = f"""CRITICAL VERIFICATION NOTICE:
The previous extraction attempt yielded insufficient verified claims ({len(verified_claims)} verified out of {len(result.claims)} proposed).
Most quotes failed character-for-character verification against the source document.
Extract at least 15 comprehensive claims where `source_quote` is copied EXACTLY, WORD-FOR-WORD, directly from the text below without alteration.

DOCUMENT CONTENT:
\"\"\"
{dossier_text}
\"\"\"
"""
        try:
            retry_result = provider.complete_structured(
                prompt=retry_prompt,
                schema=ClaimsExtractionResult,
                system_instruction=CLAIM_EXTRACTION_SYSTEM,
                temperature=0.0,
            )
            retry_verified, retry_rejected = verify_and_filter_claims(retry_result.claims, dossier_text)
            if len(retry_verified) > len(verified_claims):
                verified_claims = retry_verified
                rejected_claims = retry_rejected
        except Exception:
            pass

    return verified_claims, rejected_claims
