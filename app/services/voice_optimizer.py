"""Voice-optimization service.

Produces concise summaries and metadata that an LLM can read aloud.
Keeps responses short and information-dense for conversational AI.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


def build_voice_summary(
    source: str,
    items: List[Dict[str, Any]],
    total: int,
    filters_applied: Dict[str, Any],
) -> str:
    """Return a one- or two-sentence summary suitable for voice output.

    Parameters
    ----------
    source : str
        Data source name (crm, support, analytics).
    items : list
        The records being returned in this page.
    total : int
        Total matching records (before pagination).
    filters_applied : dict
        Active filters the user requested.
    """
    returned = len(items)

    if source == "support":
        return _summarize_support(items, total, returned, filters_applied)
    elif source == "crm":
        return _summarize_crm(items, total, returned, filters_applied)
    elif source == "analytics":
        return _summarize_analytics(items, total, returned, filters_applied)

    # Fallback
    return f"Returning {returned} of {total} records."


def freshness_label() -> str:
    """Return a human-readable data freshness string."""
    now = datetime.now(timezone.utc)
    return f"Data as of {now.strftime('%B %d, %Y %H:%M UTC')}"


# ── Support summaries ───────────────────────────────────────────────

def _summarize_support(
    items: List[Dict], total: int, returned: int, filters: Dict
) -> str:
    open_count = sum(1 for t in items if t.get("status") == "open")
    high_count = sum(1 for t in items if t.get("priority") == "high")

    parts: List[str] = []
    if filters:
        filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        parts.append(f"Filtered by {filter_desc}.")

    parts.append(f"Showing {returned} of {total} tickets.")

    if open_count:
        parts.append(f"{open_count} are open.")
    if high_count:
        parts.append(f"{high_count} are high priority.")

    return " ".join(parts)


# ── CRM summaries ──────────────────────────────────────────────────

def _summarize_crm(
    items: List[Dict], total: int, returned: int, filters: Dict
) -> str:
    active = sum(1 for c in items if c.get("status") == "active")
    inactive = returned - active

    parts: List[str] = []
    if filters:
        filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        parts.append(f"Filtered by {filter_desc}.")

    parts.append(f"Showing {returned} of {total} customers.")
    parts.append(f"{active} active, {inactive} inactive.")
    return " ".join(parts)


# ── Analytics summaries ─────────────────────────────────────────────

def _summarize_analytics(
    items: List[Dict], total: int, returned: int, filters: Dict
) -> str:
    if not items:
        return "No analytics data found for the given filters."

    values = [r.get("value", 0) for r in items]
    avg_val = sum(values) / len(values) if values else 0
    min_val = min(values) if values else 0
    max_val = max(values) if values else 0

    metric_name = items[0].get("metric", "metric")
    date_range = ""
    if len(items) >= 2:
        dates = sorted(r.get("date", "") for r in items)
        date_range = f" from {dates[0]} to {dates[-1]}"

    parts: List[str] = []
    if filters:
        filter_desc = ", ".join(f"{k}={v}" for k, v in filters.items() if v)
        parts.append(f"Filtered by {filter_desc}.")

    parts.append(
        f"Showing {returned} of {total} data points for {metric_name}{date_range}."
    )
    parts.append(
        f"Average: {avg_val:.0f}, Min: {min_val:.0f}, Max: {max_val:.0f}."
    )
    return " ".join(parts)
