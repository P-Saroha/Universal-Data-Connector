"""End-to-end API tests using FastAPI TestClient."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


# ── Health ─────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_has_version(self):
        r = client.get("/health")
        assert "version" in r.json()


# ── Data endpoints ─────────────────────────────────────────────────

class TestDataEndpoints:
    def test_get_crm_data(self):
        r = client.get("/data/crm")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "crm"
        assert len(body["data"]) > 0
        assert "metadata" in body
        assert body["metadata"]["total_results"] > 0

    def test_get_support_data(self):
        r = client.get("/data/support")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "support"
        assert len(body["data"]) > 0

    def test_get_analytics_data(self):
        r = client.get("/data/analytics")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "analytics"
        assert len(body["data"]) > 0

    def test_unknown_source_returns_404(self):
        r = client.get("/data/unknown_source")
        assert r.status_code == 404

    def test_limit_parameter(self):
        r = client.get("/data/crm", params={"limit": 3})
        body = r.json()
        assert len(body["data"]) <= 3

    def test_filter_crm_by_status(self):
        r = client.get("/data/crm", params={"status": "active"})
        body = r.json()
        for item in body["data"]:
            assert item["status"] == "active"

    def test_filter_support_by_priority(self):
        r = client.get("/data/support", params={"priority": "high"})
        body = r.json()
        for item in body["data"]:
            assert item["priority"] == "high"

    def test_filter_analytics_by_date_range(self):
        r = client.get("/data/analytics", params={
            "date_from": "2026-02-10",
            "date_to": "2026-02-15",
        })
        body = r.json()
        for item in body["data"]:
            assert "2026-02-10" <= item["date"] <= "2026-02-15"

    def test_voice_summary_present(self):
        r = client.get("/data/crm", params={"voice_mode": True})
        body = r.json()
        assert body["metadata"]["voice_summary"] is not None
        assert len(body["metadata"]["voice_summary"]) > 0

    def test_data_freshness_present(self):
        r = client.get("/data/support")
        body = r.json()
        assert "Data as of" in body["metadata"]["data_freshness"]

    def test_pagination_has_more(self):
        r = client.get("/data/crm", params={"limit": 2})
        body = r.json()
        assert body["metadata"]["has_more"] is True

    def test_filters_applied_in_metadata(self):
        r = client.get("/data/support", params={"status": "open"})
        body = r.json()
        assert body["metadata"]["filters_applied"].get("status") == "open"


# ── Convenience endpoints ──────────────────────────────────────────

class TestConvenienceEndpoints:
    def test_crm_customers(self):
        r = client.get("/data/crm/customers", params={"status": "active", "limit": 3})
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "crm"

    def test_support_tickets(self):
        r = client.get("/data/support/tickets", params={"priority": "high"})
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "support"

    def test_analytics_metrics(self):
        r = client.get("/data/analytics/metrics")
        assert r.status_code == 200
        body = r.json()
        assert body["source"] == "analytics"


# ── LLM endpoints ─────────────────────────────────────────────────

class TestLLMEndpoints:
    def test_get_tools(self):
        r = client.get("/llm/tools")
        assert r.status_code == 200
        body = r.json()
        assert "tools" in body
        assert len(body["tools"]) == 3
        names = [t["function"]["name"] for t in body["tools"]]
        assert "query_crm" in names
        assert "query_support_tickets" in names
        assert "query_analytics" in names

    def test_tools_have_parameters(self):
        r = client.get("/llm/tools")
        for tool in r.json()["tools"]:
            fn = tool["function"]
            assert "parameters" in fn
            assert "properties" in fn["parameters"]

    def test_llm_query_support(self):
        r = client.post("/llm/query", json={
            "question": "How many open support tickets are there?",
            "voice_mode": True,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["function_called"] == "query_support_tickets"
        assert len(body["answer"]) > 0

    def test_llm_query_crm(self):
        r = client.post("/llm/query", json={
            "question": "Show me active customers",
            "voice_mode": True,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["function_called"] == "query_crm"

    def test_llm_query_analytics(self):
        r = client.post("/llm/query", json={
            "question": "What are the daily active user metrics?",
            "voice_mode": True,
        })
        assert r.status_code == 200
        body = r.json()
        assert body["function_called"] == "query_analytics"

    def test_llm_query_unknown_topic(self):
        r = client.post("/llm/query", json={
            "question": "What is the meaning of life?",
            "voice_mode": True,
        })
        assert r.status_code == 200
        body = r.json()
        # Should gracefully handle unknown queries
        assert "answer" in body
