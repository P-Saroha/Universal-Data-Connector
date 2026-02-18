"""Tests for data connectors — CRM, Support, Analytics."""

import pytest
from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector


# ── CRM Connector ──────────────────────────────────────────────────

class TestCRMConnector:
    def setup_method(self):
        self.conn = CRMConnector()

    def test_fetch_returns_items(self):
        result = self.conn.fetch()
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) > 0

    def test_fetch_with_limit(self):
        result = self.conn.fetch(limit=5)
        assert len(result["items"]) <= 5

    def test_filter_by_status_active(self):
        result = self.conn.fetch(filters={"status": "active"}, limit=100)
        for item in result["items"]:
            assert item["status"] == "active"

    def test_filter_by_status_inactive(self):
        result = self.conn.fetch(filters={"status": "inactive"}, limit=100)
        for item in result["items"]:
            assert item["status"] == "inactive"

    def test_filter_by_name(self):
        result = self.conn.fetch(filters={"name": "Customer 1"}, limit=100)
        for item in result["items"]:
            assert "customer 1" in item["name"].lower()

    def test_filter_by_customer_id(self):
        result = self.conn.fetch(filters={"customer_id": 1})
        assert len(result["items"]) == 1
        assert result["items"][0]["customer_id"] == 1

    def test_pagination(self):
        page1 = self.conn.fetch(limit=5, offset=0)
        page2 = self.conn.fetch(limit=5, offset=5)
        ids_1 = {r["customer_id"] for r in page1["items"]}
        ids_2 = {r["customer_id"] for r in page2["items"]}
        assert ids_1.isdisjoint(ids_2), "Pages should not overlap"

    def test_has_more(self):
        result = self.conn.fetch(limit=3, offset=0)
        assert result["has_more"] is True

    def test_sort_by_name_asc(self):
        result = self.conn.fetch(sort_by="name", sort_order="asc", limit=50)
        names = [r["name"] for r in result["items"]]
        assert names == sorted(names)


# ── Support Connector ──────────────────────────────────────────────

class TestSupportConnector:
    def setup_method(self):
        self.conn = SupportConnector()

    def test_fetch_returns_items(self):
        result = self.conn.fetch()
        assert len(result["items"]) > 0

    def test_filter_by_status_open(self):
        result = self.conn.fetch(filters={"status": "open"}, limit=100)
        for item in result["items"]:
            assert item["status"] == "open"

    def test_filter_by_priority_high(self):
        result = self.conn.fetch(filters={"priority": "high"}, limit=100)
        for item in result["items"]:
            assert item["priority"] == "high"

    def test_filter_by_customer_id(self):
        result = self.conn.fetch(filters={"customer_id": 16}, limit=100)
        for item in result["items"]:
            assert item["customer_id"] == 16

    def test_default_sort_open_high_priority_first(self):
        result = self.conn.fetch(limit=100)
        items = result["items"]
        # First item should be open (not closed)
        open_items = [i for i in items if i["status"] == "open"]
        if open_items:
            assert items[0]["status"] == "open"

    def test_filter_by_subject(self):
        result = self.conn.fetch(filters={"subject": "Issue 1"}, limit=100)
        for item in result["items"]:
            assert "issue 1" in item["subject"].lower()


# ── Analytics Connector ────────────────────────────────────────────

class TestAnalyticsConnector:
    def setup_method(self):
        self.conn = AnalyticsConnector()

    def test_fetch_returns_items(self):
        result = self.conn.fetch()
        assert len(result["items"]) > 0

    def test_filter_by_metric(self):
        result = self.conn.fetch(filters={"metric": "daily_active_users"}, limit=100)
        for item in result["items"]:
            assert item["metric"] == "daily_active_users"

    def test_filter_by_date_range(self):
        result = self.conn.fetch(
            filters={"date_from": "2026-02-10", "date_to": "2026-02-15"},
            limit=100,
        )
        for item in result["items"]:
            assert "2026-02-10" <= item["date"] <= "2026-02-15"

    def test_default_sort_newest_first(self):
        result = self.conn.fetch(limit=10)
        dates = [r["date"] for r in result["items"]]
        assert dates == sorted(dates, reverse=True)

    def test_total_count(self):
        result = self.conn.fetch(limit=5)
        assert result["total"] >= result["page_size"]
