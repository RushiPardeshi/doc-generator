"""Tests for web app endpoints and quota management."""

from fastapi.testclient import TestClient
from src.web.app import app
from src.web.quota import consume_claude_quota, check_claude_quota, get_db_connection

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
