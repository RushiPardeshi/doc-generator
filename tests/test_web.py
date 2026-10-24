"""Tests for web app endpoints and quota management."""

from fastapi.testclient import TestClient
from src.web.app import app
from src.web.quota import (
    consume_claude_quota,
    check_claude_quota,
    consume_gemini_quota,
    check_gemini_quota,
    get_db_connection,
)

client = TestClient(app)


def test_health():
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_index_page():
    res = client.get("/")
    assert res.status_code == 200
    assert "Thesis Engine" in res.text
    assert "Grounded Web Research" in res.text
    assert "headerSearchBarContainer" in res.text
    assert "headerTopicInput" in res.text
    assert "collapsedQuickBar" in res.text
    assert "leftConfigCol" in res.text


def test_quota_endpoint():
    email = "quota_endpoint_test@example.com"
    # Clean up before test
    with get_db_connection() as conn:
        conn.execute("DELETE FROM free_claude_quota WHERE email = ?", (email,))
        conn.commit()

    # Initial check
    res = client.get(f"/api/quota?email={email}")
    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["remaining"] == 3
    assert data["max"] == 3

    # Consume 3
    for _ in range(3):
        consume_claude_quota(email)

    res_after = client.get(f"/api/quota?email={email}")
    assert res_after.status_code == 200
    data_after = res_after.json()
    assert data_after["allowed"] is False
    assert data_after["remaining"] == 0

    # Clean up after test
    with get_db_connection() as conn:
        conn.execute("DELETE FROM free_claude_quota WHERE email = ?", (email,))
        conn.commit()


def test_gemini_quota_endpoint():
    email = "gemini_quota_test@example.com"
    # Clean up before test
    with get_db_connection() as conn:
        conn.execute("DELETE FROM free_provider_quota WHERE provider = 'gemini' AND email = ?", (email,))
        conn.commit()

    # Initial check
    res = client.get(f"/api/quota?email={email}&provider=gemini")
    assert res.status_code == 200
    data = res.json()
    assert data["allowed"] is True
    assert data["remaining"] == 3
    assert data["max"] == 3
    assert data["provider"] == "gemini"

    # Consume 3
    for _ in range(3):
        consume_gemini_quota(email)

    res_after = client.get(f"/api/quota?email={email}&provider=gemini")
    assert res_after.status_code == 200
    data_after = res_after.json()
    assert data_after["allowed"] is False
    assert data_after["remaining"] == 0

    # Clean up after test
    with get_db_connection() as conn:
        conn.execute("DELETE FROM free_provider_quota WHERE provider = 'gemini' AND email = ?", (email,))
        conn.commit()


def test_classify_api_endpoint():
    # Test company query
    res_company = client.post("/api/classify", json={"query": "NVDA"})
    assert res_company.status_code == 200
    assert res_company.json()["category"] == "company"
    assert res_company.json()["allow_recommendations"] is True

    # Test topic query
    res_topic = client.post("/api/classify", json={"query": "Quantum error correction algorithms"})
    assert res_topic.status_code == 200
    assert res_topic.json()["category"] == "topic"
    assert res_topic.json()["allow_recommendations"] is False


def test_bundle_api_endpoint():
    # Company bundle preview
    res_co = client.post("/api/bundle", json={"query": "NVDA", "generate_output": False})
    assert res_co.status_code == 200
    data_co = res_co.json()
    assert data_co["decision"]["category"] == "company"
    assert data_co["financial_metrics"] is not None
    assert "Real-Time Financial Snapshot" in data_co["assembled_prompt"]

    # Topic bundle preview
    res_top = client.post("/api/bundle", json={"query": "Topological quantum computing", "generate_output": False})
    assert res_top.status_code == 200
    data_top = res_top.json()
    assert data_top["decision"]["category"] == "topic"
    assert data_top["decision"]["allow_recommendations"] is False
    assert len(data_top["references"]) > 0
    assert "DO NOT recommend any suggestions" in data_top["assembled_prompt"]


