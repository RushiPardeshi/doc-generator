"""Tests for SerpApi and scholarly literature tools."""

from src.tools.serp_research import (
    ResearchReference,
    fetch_authoritative_research,
    compile_references_to_dossier_section,
)


def test_research_reference_formatting():
    ref = ResearchReference(
        title="Scaling Laws for Neural Language Models",
        authors=["Kaplan, J.", "McCandlish, S.", "Henighan, T."],
        year=2020,
        snippet="Cross-entropy loss scales as a power-law with compute, dataset size, and parameter count.",
        link="https://arxiv.org/abs/2001.08361",
        citation_count=3500,
        source="google_scholar",
    )
    formatted = ref.format_citation(index=1)
    assert "[1] Kaplan, J., McCandlish, S., Henighan, T. (2020)" in formatted
    assert "Scaling Laws for Neural Language Models" in formatted
    assert "[Cited by 3500]" in formatted
    assert "https://arxiv.org/abs/2001.08361" in formatted


def test_fetch_authoritative_research_fallback():
    refs = fetch_authoritative_research(
        "Quantum error correction",
        serpapi_key="mock_synthetic_serp_key_987654",
    )
    assert len(refs) > 0
    assert any("Quantum Error Correction" in r.title for r in refs)

    section = compile_references_to_dossier_section(refs)
    assert "## Verified Research References & Empirical Literature" in section
    assert "[1]" in section
