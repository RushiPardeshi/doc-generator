"""Unit tests for Deterministic Anti-Slop Linter."""

from src.voice.linter import lint_memo


def test_linter_detects_ai_cliches():
    text = """
    Apex is not only a monitoring tool, but also a strategic platform.
    Its rapid growth is a testament to its engineering culture.
    As we delve into the rapidly evolving landscape, Apex is poised to capture the market.
    """
    result = lint_memo(text)
    assert result.is_acceptable is False
    assert result.slop_score > 30.0

    violations_desc = " ".join(v.rule_description for v in result.violations)
    assert "Correlative conjunction" in violations_desc
    assert "testament to" in violations_desc
    assert "delve" in violations_desc
    assert "landscape" in violations_desc
    assert "poised to" in violations_desc


def test_linter_detects_em_dash_clusters():
    text = """
    Apex provides observability — a critical need — across all cloud hosts.
    The platform ingests telemetry — metrics, traces, and logs — at high throughput.
    Furthermore — as seen in H1 results — margins expanded — creating cash flow.
    """
    result = lint_memo(text)
    assert result.em_dash_count >= 4
    assert any("Em-dash overuse" in v.rule_description for v in result.violations)


def test_clean_analyst_prose_passes():
    text = """
    # Investment Memo: Apex Systems
    Apex reported $153.3 million in H1 2019 revenue, growing 79% year-over-year.
    Dollar-based net expansion reached 146%. The company generated $10.9 million in operating cash flow.
    The primary risk is AWS native monitoring bundling. If gross margins drop below 70%, the thesis fails.
    """
    result = lint_memo(text)
    assert len(result.violations) == 0
    assert result.em_dash_count == 0
    assert result.rule_of_three_count == 0
    assert result.slop_score < 15.0
    assert result.is_acceptable is True
