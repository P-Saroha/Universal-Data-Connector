"""Pydantic models for Analytics / Metrics data."""

import datetime as _dt

from pydantic import BaseModel, Field


class AnalyticsMetric(BaseModel):
    """Represents a single analytics data point."""
    metric: str = Field(..., description="Metric name (e.g. daily_active_users)")
    date: _dt.date = Field(..., description="Date of the measurement")
    value: float = Field(..., description="Metric value")
