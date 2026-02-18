"""Abstract base class for all data connectors."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class BaseConnector(ABC):
    """Base interface that every data-source connector must implement.

    Provides consistent data access with filtering, sorting, and pagination
    for the voice-optimized data pipeline.
    """

    source_name: str = "base"
    data_file: str = ""

    def __init__(self, data_dir: str | None = None) -> None:
        from app.config import settings
        self._data_dir = Path(data_dir or settings.DATA_DIR)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fetch(
        self,
        filters: Dict[str, Any] | None = None,
        sort_by: str | None = None,
        sort_order: str = "desc",
        limit: int = 10,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Fetch data with optional filters, sorting, and pagination.

        Returns a dict with keys: items, total, page, page_size, has_more
        """
        logger.info(
            "Fetching from %s | filters=%s sort=%s limit=%d offset=%d",
            self.source_name, filters, sort_by, limit, offset,
        )

        raw = self._load_data()
        filtered = self._apply_filters(raw, filters or {})
        sorted_data = self._apply_sort(filtered, sort_by, sort_order)

        total = len(sorted_data)
        page_data = sorted_data[offset: offset + limit]
        page = (offset // limit) + 1 if limit else 1

        return {
            "items": page_data,
            "total": total,
            "page": page,
            "page_size": limit,
            "has_more": (offset + limit) < total,
        }

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    @abstractmethod
    def _apply_filters(
        self, data: List[Dict[str, Any]], filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Apply source-specific filters.  Must be overridden."""
        ...

    def _apply_sort(
        self,
        data: List[Dict[str, Any]],
        sort_by: str | None,
        sort_order: str,
    ) -> List[Dict[str, Any]]:
        """Sort data by a given field.  Subclasses may override for custom logic."""
        if not sort_by or not data:
            return data
        if sort_by not in data[0]:
            logger.warning("Sort field '%s' not found in %s data", sort_by, self.source_name)
            return data
        try:
            return sorted(data, key=lambda r: r.get(sort_by, ""), reverse=(sort_order == "desc"))
        except TypeError:
            logger.warning("Cannot sort %s by '%s' — mixed types", self.source_name, sort_by)
            return data

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_data(self) -> List[Dict[str, Any]]:
        """Load raw JSON data from disk."""
        path = self._data_dir / self.data_file
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            logger.debug("Loaded %d records from %s", len(data), path)
            return data
        except FileNotFoundError:
            logger.error("Data file not found: %s", path)
            return []
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON in %s: %s", path, exc)
            return []

    def get_schema_description(self) -> Dict[str, Any]:
        """Return metadata describing this connector for LLM function calling."""
        return {
            "source": self.source_name,
            "description": self.__class__.__doc__ or "",
            "supported_filters": self._supported_filters(),
            "supported_sort_fields": self._supported_sort_fields(),
        }

    @abstractmethod
    def _supported_filters(self) -> List[Dict[str, str]]:
        """Return list of {name, type, description} for this connector's filters."""
        ...

    @abstractmethod
    def _supported_sort_fields(self) -> List[str]:
        """Return field names that can be used for sorting."""
        ...
