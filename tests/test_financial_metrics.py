"""Tests for real-time company financial metrics fetcher."""

from src.tools.financial_metrics import (
    CompanyFinancialMetrics,
    fetch_financial_metrics,
)


def test_synthetic_metrics_generation():
    metrics = fetch_financial_metrics("NVDA", api_key="mock_synthetic_fmp_token_12345")
    assert metrics.ticker == "NVDA"
    assert metrics.price is not None
    assert metrics.market_cap is not None
    assert metrics.pe_ttm is not None
    assert metrics.ev_to_ebitda is not None
    assert metrics.gross_margin is not None


def test_metrics_markdown_formatting():
    metrics = CompanyFinancialMetrics(
        company_name="Apex Systems",
        ticker="APEX",
        currency="USD",
        price=150.0,
        market_cap=1_500_000_000_000.0,
        pe_ttm=25.0,
        pe_forward=20.0,
        ev_to_ebitda=18.0,
        price_to_sales=10.0,
        revenue_ttm=60_000_000_000.0,
        revenue_growth_yoy=0.25,
        gross_margin=0.60,
        operating_margin=0.35,
        net_margin=0.28,
        free_cash_flow_ttm=15_000_000_000.0,
        net_debt_to_ebitda=0.2,
        source="synthetic_test",
    )
    md = metrics.format_as_markdown()
    assert "Real-Time Financial Snapshot: Apex Systems (APEX)" in md
    assert "$1.50T" in md
    assert "25.0x" in md
    assert "25.0%" in md
