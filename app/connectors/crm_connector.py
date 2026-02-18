"""Connector for Customer / CRM data."""

import logging
from typing import Any, Dict, List
from .base import BaseConnector

logger = logging.getLogger(__name__)


class CRMConnector(BaseConnector):
    """Access customer CRM records with filtering by status, name, email, and customer ID."""

    source_name = "crm"
    data_file = "customers.json"

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

        if "name" in filters and filters["name"]:
            query = filters["name"].lower()
            result = [r for r in result if query in r.get("name", "").lower()]

        if "email" in filters and filters["email"]:
            query = filters["email"].lower()
            result = [r for r in result if query in r.get("email", "").lower()]

        if "customer_id" in filters and filters["customer_id"] is not None:
            cid = int(filters["customer_id"])
            result = [r for r in result if r.get("customer_id") == cid]

        logger.info("CRM filter: %d → %d records", len(data), len(result))
        return result

    # ------------------------------------------------------------------
    # Schema helpers
    # ------------------------------------------------------------------

    def _supported_filters(self) -> List[Dict[str, str]]:
        return [
            {"name": "status", "type": "string", "description": "Filter by customer status (active / inactive)"},
            {"name": "name", "type": "string", "description": "Search customers by name (partial match)"},
            {"name": "email", "type": "string", "description": "Search customers by email (partial match)"},
            {"name": "customer_id", "type": "integer", "description": "Exact customer ID lookup"},
        ]

    def _supported_sort_fields(self) -> List[str]:
        return ["customer_id", "name", "created_at", "status"]
