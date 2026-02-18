"""Business rules engine for voice-optimized data delivery.

Rules are applied *after* connector filtering and *before* voice optimization
to ensure data relevance and brevity for conversational AI.
"""

import logging
from typing import Any, Dict, List

from app.config import settings

logger = logging.getLogger(__name__)

# ── Priority maps used for scoring ──────────────────────────────────
_PRIORITY_SCORE = {"high": 3, "medium": 2, "low": 1}
_STATUS_SCORE_TICKETS = {"open": 2, "closed": 1}
_STATUS_SCORE_CRM = {"active": 2, "inactive": 1}


def apply_business_rules(
    source: str,
    data: List[Dict[str, Any]],
    limit: int | None = None,
) -> List[Dict[str, Any]]:
    """Apply source-specific business rules and trim to voice limit.

    Parameters
    ----------
    source : str
        Data source name (crm, support, analytics).
    data : list
        Pre-filtered records from a connector.
    limit : int, optional
        Maximum records to keep.  Defaults to ``MAX_VOICE_RESULTS``.

    Returns
    -------
    list
        Re-ordered and trimmed records.
    """
    max_items = limit or settings.MAX_VOICE_RESULTS

    if source == "support":
        data = _prioritize_support(data)
    elif source == "crm":
        data = _prioritize_crm(data)
    elif source == "analytics":
        data = _prioritize_analytics(data)

    trimmed = data[:max_items]
    logger.info(
        "Business rules [%s]: %d → %d records (limit %d)",
        source, len(data), len(trimmed), max_items,
    )
    return trimmed


# ── Source-specific rules ────────────────────────────────────────────

def _prioritize_support(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Open + high-priority tickets first, then by most recent."""
    return sorted(
        data,
        key=lambda r: (
            -_STATUS_SCORE_TICKETS.get(r.get("status", ""), 0),
            -_PRIORITY_SCORE.get(r.get("priority", ""), 0),
            r.get("created_at", ""),
        ),
        reverse=False,
    )


def _prioritize_crm(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Active customers first, then most recently created."""
    return sorted(
        data,
        key=lambda r: (
            -_STATUS_SCORE_CRM.get(r.get("status", ""), 0),
            r.get("created_at", ""),
        ),
        reverse=False,
    )


def _prioritize_analytics(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Most recent metrics first (already handled by connector, but enforced here)."""
    return sorted(data, key=lambda r: r.get("date", ""), reverse=True)
