"""Data access endpoints — unified interface for LLM function calling.

Each endpoint:
1. Routes to the correct connector
2. Applies filters from query params
3. Runs business rules (prioritisation)
4. Generates a voice-optimised summary in metadata
"""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.connectors.crm_connector import CRMConnector
from app.connectors.support_connector import SupportConnector
from app.connectors.analytics_connector import AnalyticsConnector
from app.models.common import DataResponse, DataType, Metadata
from app.services.business_rules import apply_business_rules
from app.services.data_identifier import identify_data_type
from app.services.voice_optimizer import build_voice_summary, freshness_label

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/data", tags=["Data"])

# Connector registry (singleton-ish for the process lifetime)
_CONNECTORS = {
    "crm": CRMConnector,
    "support": SupportConnector,
    "analytics": AnalyticsConnector,
}


# ── Generic endpoint ───────────────────────────────────────────────

@router.get(
    "/{source}",
    response_model=DataResponse,
    summary="Query any data source",
    description=(
        "Unified data endpoint.  Pass `source` as **crm**, **support**, or **analytics**.  "
        "All query-string parameters are forwarded as filters to the connector."
    ),
)
def get_data(
    source: str,
    limit: int = Query(10, ge=1, le=100, description="Max results to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    voice_mode: bool = Query(True, description="Enable voice-optimised responses"),
    # ── CRM filters ─────────────────────────────────────────────
    status: Optional[str] = Query(None, description="Filter by status"),
    name: Optional[str] = Query(None, description="Search by name (CRM)"),
    email: Optional[str] = Query(None, description="Search by email (CRM)"),
    customer_id: Optional[int] = Query(None, description="Filter by customer ID"),
    # ── Support filters ─────────────────────────────────────────
    priority: Optional[str] = Query(None, description="Filter by priority (support)"),
    subject: Optional[str] = Query(None, description="Search by subject (support)"),
    # ── Analytics filters ───────────────────────────────────────
    metric: Optional[str] = Query(None, description="Filter by metric name"),
    date_from: Optional[str] = Query(None, description="Start date YYYY-MM-DD"),
    date_to: Optional[str] = Query(None, description="End date YYYY-MM-DD"),
):
    if source not in _CONNECTORS:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown data source '{source}'. Available: {list(_CONNECTORS.keys())}",
        )

    # Build filters dict from provided query params
    filters = _build_filters(
        status=status, name=name, email=email, customer_id=customer_id,
        priority=priority, subject=subject,
        metric=metric, date_from=date_from, date_to=date_to,
    )

    connector = _CONNECTORS[source]()
    result = connector.fetch(
        filters=filters,
        sort_by=sort_by,
        sort_order=sort_order,
        limit=1000,     # fetch all matching, let business rules trim
        offset=0,
    )

    all_items = result["items"]
    total = result["total"]

    # Business rules (prioritise + trim for voice)
    ruled = apply_business_rules(source, all_items, limit=limit)

    # Paginate the ruled set
    page_items = ruled[offset: offset + limit]
    data_type = identify_data_type(page_items)

    # Voice summary
    voice_summary = None
    if voice_mode:
        voice_summary = build_voice_summary(source, page_items, total, filters)

    metadata = Metadata(
        total_results=total,
        returned_results=len(page_items),
        page=(offset // limit) + 1 if limit else 1,
        page_size=limit,
        has_more=(offset + limit) < total,
        data_type=data_type,
        data_freshness=freshness_label(),
        voice_summary=voice_summary,
        filters_applied=filters,
    )

    return DataResponse(source=source, data=page_items, metadata=metadata)


# ── Convenience endpoints for each source ───────────────────────────

@router.get(
    "/crm/customers",
    response_model=DataResponse,
    summary="Query CRM customers",
    description="Retrieve customer records with optional filters for status, name, email.",
)
def get_customers(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    voice_mode: bool = Query(True),
    status: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
):
    return get_data(
        source="crm", limit=limit, offset=offset,
        sort_by=sort_by, sort_order=sort_order, voice_mode=voice_mode,
        status=status, name=name, email=email, customer_id=customer_id,
        priority=None, subject=None, metric=None, date_from=None, date_to=None,
    )


@router.get(
    "/support/tickets",
    response_model=DataResponse,
    summary="Query support tickets",
    description="Retrieve support tickets with optional filters for status, priority, customer_id.",
)
def get_tickets(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    voice_mode: bool = Query(True),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    customer_id: Optional[int] = Query(None),
    subject: Optional[str] = Query(None),
):
    return get_data(
        source="support", limit=limit, offset=offset,
        sort_by=sort_by, sort_order=sort_order, voice_mode=voice_mode,
        status=status, name=None, email=None, customer_id=customer_id,
        priority=priority, subject=subject, metric=None, date_from=None, date_to=None,
    )


@router.get(
    "/analytics/metrics",
    response_model=DataResponse,
    summary="Query analytics metrics",
    description="Retrieve analytics data points with optional filters for metric name and date range.",
)
def get_metrics(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
    sort_by: Optional[str] = Query(None),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    voice_mode: bool = Query(True),
    metric: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    return get_data(
        source="analytics", limit=limit, offset=offset,
        sort_by=sort_by, sort_order=sort_order, voice_mode=voice_mode,
        status=None, name=None, email=None, customer_id=None,
        priority=None, subject=None, metric=metric, date_from=date_from, date_to=date_to,
    )


# ── Helpers ─────────────────────────────────────────────────────────

def _build_filters(**kwargs) -> dict:
    """Strip ``None`` values so connectors only see active filters."""
    return {k: v for k, v in kwargs.items() if v is not None}
