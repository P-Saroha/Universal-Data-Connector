"""Connector for Analytics / Metrics data."""

import logging
from datetime import date, datetime
from typing import Any, Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)


class AnalyticsConnector(BaseConnector):
    """Access analytics metrics with filtering by metric name and date range."""

    source_name = "analytics"
    data_file = "analytics.json"

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filters(
        self, data: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        result = data

        if "metric" in filters and filters["metric"]:
            val = filters["metric"].lower()
            result = [r for r in result if r.get("metric", "").lower() == val]

        if "date_from" in filters and filters["date_from"]:
            cutoff = str(filters["date_from"])
            result = [r for r in result if r.get("date", "") >= cutoff]

        if "date_to" in filters and filters["date_to"]:
            cutoff = str(filters["date_to"])
            result = [r for r in result if r.get("date", "") <= cutoff]

        logger.info("Analytics filter: %d → %d records", len(data), len(result))
        return result

    # ------------------------------------------------------------------
    # Default sort: newest date first
    # ------------------------------------------------------------------

    def _apply_sort(
        self,
        data: List[Dict[str, Any]],
        sort_by: str | None,
        sort_order: str,
    ) -> List[Dict[str, Any]]:
        if sort_by:
            return super()._apply_sort(data, sort_by, sort_order)
        return sorted(data, key=lambda r: r.get("date", ""), reverse=True)

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def _supported_filters(self) -> List[Dict[str, str]]:
        return [
            {"name": "metric", "type": "string", "description": "Filter by metric name (e.g. daily_active_users)"},
            {"name": "date_from", "type": "string (YYYY-MM-DD)", "description": "Start date (inclusive)"},
            {"name": "date_to", "type": "string (YYYY-MM-DD)", "description": "End date (inclusive)"},
        ]

    def _supported_sort_fields(self) -> List[str]:
        return ["date", "value", "metric"]
