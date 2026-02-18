"""Tests for business rules engine."""

import pytest
from app.services.business_rules import apply_business_rules


# ── Sample data ────────────────────────────────────────────────────

TICKETS = [
    {"ticket_id": 1, "status": "closed", "priority": "low", "created_at": "2026-01-01"},
    {"ticket_id": 2, "status": "open", "priority": "high", "created_at": "2026-02-01"},
    {"ticket_id": 3, "status": "open", "priority": "medium", "created_at": "2026-02-10"},
    {"ticket_id": 4, "status": "open", "priority": "high", "created_at": "2026-02-15"},
    {"ticket_id": 5, "status": "closed", "priority": "high", "created_at": "2026-02-05"},
]

CUSTOMERS = [
    {"customer_id": 1, "status": "inactive", "created_at": "2025-01-01"},
    {"customer_id": 2, "status": "active", "created_at": "2025-06-01"},
    {"customer_id": 3, "status": "active", "created_at": "2026-01-01"},
    {"customer_id": 4, "status": "inactive", "created_at": "2025-12-01"},
]

ANALYTICS = [
    {"metric": "dau", "date": "2026-02-01", "value": 100},
    {"metric": "dau", "date": "2026-02-03", "value": 300},
    {"metric": "dau", "date": "2026-02-02", "value": 200},
]


class TestSupportRules:
    def test_open_tickets_come_first(self):
        result = apply_business_rules("support", TICKETS, limit=10)
        open_indices = [i for i, t in enumerate(result) if t["status"] == "open"]
        closed_indices = [i for i, t in enumerate(result) if t["status"] == "closed"]
        if open_indices and closed_indices:
            assert max(open_indices) < min(closed_indices)

    def test_high_priority_before_low(self):
        result = apply_business_rules("support", TICKETS, limit=10)
        open_tickets = [t for t in result if t["status"] == "open"]
        if len(open_tickets) >= 2:
            assert open_tickets[0]["priority"] == "high"

    def test_limit_respected(self):
        result = apply_business_rules("support", TICKETS, limit=2)
        assert len(result) == 2


class TestCRMRules:
    def test_active_customers_first(self):
        result = apply_business_rules("crm", CUSTOMERS, limit=10)
        statuses = [c["status"] for c in result]
        # Active should appear before inactive
        active_indices = [i for i, s in enumerate(statuses) if s == "active"]
        inactive_indices = [i for i, s in enumerate(statuses) if s == "inactive"]
        if active_indices and inactive_indices:
            assert max(active_indices) < min(inactive_indices)

    def test_limit_respected(self):
        result = apply_business_rules("crm", CUSTOMERS, limit=2)
        assert len(result) == 2


class TestAnalyticsRules:
    def test_newest_first(self):
        result = apply_business_rules("analytics", ANALYTICS, limit=10)
        dates = [r["date"] for r in result]
        assert dates == sorted(dates, reverse=True)

    def test_empty_data(self):
        result = apply_business_rules("analytics", [], limit=10)
        assert result == []
