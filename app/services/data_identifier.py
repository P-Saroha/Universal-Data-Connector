"""Data-type identification service.

Inspects a dataset and classifies its structure so downstream
services (voice optimizer, LLM) can apply appropriate transformations.
"""

import logging
from typing import Any, Dict, List

from app.models.common import DataType

logger = logging.getLogger(__name__)

# Fields that hint at a date / time-series dimension
_TIME_FIELDS = {"date", "timestamp", "created_at", "updated_at", "time"}


def identify_data_type(data: List[Dict[str, Any]]) -> DataType:
    """Classify a list of records into a ``DataType``.

    Heuristics
    ----------
    * If the data is empty → ``EMPTY``
    * If any top-level key looks like a date field → ``TIME_SERIES``
    * If records have nested dicts/lists → ``HIERARCHICAL``
    * Otherwise → ``TABULAR``
    """
    if not data:
        return DataType.EMPTY

    sample = data[0]
    keys = set(sample.keys())

    # Check for time-series
    if keys & _TIME_FIELDS:
        logger.debug("Detected TIME_SERIES (fields: %s)", keys & _TIME_FIELDS)
        return DataType.TIME_SERIES

    # Check for hierarchical / nested
    for val in sample.values():
        if isinstance(val, (dict, list)):
            logger.debug("Detected HIERARCHICAL data")
            return DataType.HIERARCHICAL

    logger.debug("Detected TABULAR data")
    return DataType.TABULAR
