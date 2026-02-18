"""Connector for Support Ticket data."""

import logging
from typing import Any, Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)


class SupportConnector(BaseConnector):
    """Access support tickets with filtering by status, priority, and customer ID."""

    source_name = "support"
    data_file = "support_tickets.json"

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def _apply_filters(
        self, data: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        result = data

        if "status" in filters and filters["status"]:
            val = filters["status"].lower()
            result = [r for r in result if r.get("status", "").lower() == val]

        if "priority" in filters and filters["priority"]:
            val = filters["priority"].lower()
            result = [r for r in result if r.get("priority", "").lower() == val]

        if "customer_id" in filters and filters["customer_id"] is not None:
            cid = int(filters["customer_id"])
            result = [r for r in result if r.get("customer_id") == cid]

        if "subject" in filters and filters["subject"]:
            query = filters["subject"].lower()
            result = [r for r in result if query in r.get("subject", "").lower()]

        logger.info("Support filter: %d → %d records", len(data), len(result))
        return result

    # ------------------------------------------------------------------
    # Custom sort: open + high-priority tickets first by default
    # ------------------------------------------------------------------

    _PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
    _STATUS_ORDER = {"open": 0, "closed": 1}

    def _apply_sort(
        self,
        data: List[Dict[str, Any]],
        sort_by: str | None,
        sort_order: str,
    ) -> List[Dict[str, Any]]:
        if sort_by:
            return super()._apply_sort(data, sort_by, sort_order)
        # Default: open first, then by priority, then newest
        return sorted(
            data,
            key=lambda r: (
                self._STATUS_ORDER.get(r.get("status", ""), 9),
                self._PRIORITY_ORDER.get(r.get("priority", ""), 9),
                r.get("created_at", ""),
            ),
        )

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def _supported_filters(self) -> List[Dict[str, str]]:
        return [
            {"name": "status", "type": "string", "description": "Filter by ticket status (open / closed)"},
            {"name": "priority", "type": "string", "description": "Filter by priority (high / medium / low)"},
            {"name": "customer_id", "type": "integer", "description": "Filter tickets by customer ID"},
            {"name": "subject", "type": "string", "description": "Search tickets by subject (partial match)"},
        ]

    def _supported_sort_fields(self) -> List[str]:
        return ["ticket_id", "priority", "created_at", "status"]
