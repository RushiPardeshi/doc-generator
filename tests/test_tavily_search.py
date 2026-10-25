"""Tests for Tavily search tool and formatting."""

from src.tools.tavily_search import (
    fetch_tavily_search,
    format_tavily_dossier,
)


def test_format_tavily_dossier():
    sample_results = [
        {
            "title": "What Is Terafab? Musk's Chip Fab Explained",
            "url": "https://example.com/terafab",
            "content": "Terafab is a planned semiconductor fabrication plant developed jointly by Tesla, SpaceX and Intel. It aims to consolidate all chip manufacturing under one roof.",
        },
        {
            "title": "Terafab: The World's Next Generation Chip Factory",
            "url": "https://example.com/next-gen-fab",
            "content": "The reported $119B vision aims to free Tesla and SpaceX from external silicon dependencies.",
        },
    ]

    dossier = format_tavily_dossier(sample_results, "terafab")
    assert "# Research Dossier: Terafab" in dossier
    assert "https://example.com/terafab" in dossier
    assert "Terafab is a planned semiconductor fabrication plant" in dossier
    assert "Key Factual Statements & Quotes" in dossier


def test_tavily_search_mock_handling():
    # Synthetic mock key shouldn't crash
    results = fetch_tavily_search("quantum computing", api_key="tvly-mock_key_synthetic_test")
    assert isinstance(results, list)
