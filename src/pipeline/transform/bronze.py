"""Bronze-layer helpers that preserve source data and add technical metadata."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import pandas as pd


def add_ingestion_metadata(
    frame: pd.DataFrame,
    *,
    run_id: str,
    source_system: str,
    source_table: str,
    extract_type: str,
    watermark_value: Any = None,
    ingested_at: datetime | None = None,
) -> pd.DataFrame:
    """Return a copy enriched with the mandatory Bronze metadata."""
    result = frame.copy()
    timestamp = ingested_at or datetime.now(timezone.utc)
    result["_ingested_at"] = timestamp
    result["_pipeline_run_id"] = run_id
    result["_source_system"] = source_system
    result["_source_table"] = source_table
    result["_extract_type"] = extract_type
    result["_watermark_value"] = (
        None if watermark_value is None else str(watermark_value)
    )
    return result
