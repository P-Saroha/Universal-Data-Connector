"""Shared Pydantic models used across all data sources."""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional
from enum import Enum


class DataType(str, Enum):
    """Detected data structure type."""
    TABULAR = "tabular"
    TIME_SERIES = "time_series"
    HIERARCHICAL = "hierarchical"
    UNKNOWN = "unknown"
    EMPTY = "empty"


class QueryParams(BaseModel):
    """Common query parameters accepted by all data endpoints."""
    limit: int = Field(10, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(0, ge=0, description="Number of results to skip (pagination)")
    sort_by: Optional[str] = Field(None, description="Field name to sort by")
    sort_order: str = Field("desc", pattern="^(asc|desc)$", description="Sort direction")
    voice_mode: bool = Field(True, description="Enable voice-optimized responses")


class Metadata(BaseModel):
    """Response metadata providing context about the returned data."""
    total_results: int = Field(..., description="Total matching records in the source")
    returned_results: int = Field(..., description="Number of records in this response")
    page: int = Field(1, description="Current page number (1-based)")
    page_size: int = Field(10, description="Results per page")
    has_more: bool = Field(False, description="Whether more results are available")
    data_type: DataType = Field(DataType.UNKNOWN, description="Detected data structure type")
    data_freshness: str = Field(..., description="Human-readable data freshness indicator")
    voice_summary: Optional[str] = Field(None, description="Concise summary optimized for voice output")
    filters_applied: Dict[str, Any] = Field(default_factory=dict, description="Active filters on this response")


class DataResponse(BaseModel):
    """Standard envelope returned by all data endpoints."""
    source: str = Field(..., description="Data source name (crm, support, analytics)")
    data: List[Any] = Field(default_factory=list, description="Result records")
    metadata: Metadata
