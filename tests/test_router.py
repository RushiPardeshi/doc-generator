"""Tests for intent routing and query classification."""

import pytest
from src.routing.models import QueryCategory, RoutingDecision
from src.routing.classifier import classify_query, _heuristic_classify


def test_heuristic_classify_company():
    # Ticker pattern
    res = _heuristic_classify("NVDA")
    assert res.category == QueryCategory.COMPANY
    assert res.allow_recommendations is True
    assert "NVDA" in res.tickers

    # Known company name
    res2 = _heuristic_classify("Apple")
    assert res2.category == QueryCategory.COMPANY
    assert res2.allow_recommendations is True


def test_heuristic_classify_topic():
    res = _heuristic_classify("Quantum error correction algorithms in topological qubits")
    assert res.category == QueryCategory.TOPIC
    assert res.allow_recommendations is False
    assert "serp_scholar" in res.data_sources


def test_heuristic_classify_industry():
    res = _heuristic_classify("Global semiconductor lithography market size and CAGR")
    assert res.category == QueryCategory.INDUSTRY
    assert res.allow_recommendations is False


def test_heuristic_classify_comparison():
    res = _heuristic_classify("Snowflake vs Databricks")
    assert res.category == QueryCategory.COMPARISON
    assert len(res.primary_entities) == 2
    assert "Snowflake" in res.primary_entities
    assert "Databricks" in res.primary_entities


def test_heuristic_classify_macro():
    res = _heuristic_classify("Impact of Fed interest rate cuts on treasury yields")
    assert res.category == QueryCategory.MACRO
    assert res.allow_recommendations is False


def test_heuristic_classify_ambiguous():
    res = _heuristic_classify("Mercury")
    assert res.category == QueryCategory.AMBIGUOUS
    assert res.disambiguation_options is not None
    assert len(res.disambiguation_options) >= 2


def test_classify_query_empty_fails():
    with pytest.raises(ValueError):
        classify_query("")
