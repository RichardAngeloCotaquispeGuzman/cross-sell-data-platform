"""Extraction from Neon PostgreSQL with incremental sales watermarks."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Final

import pandas as pd
from sqlalchemy import Engine, create_engine, text

from pipeline.config import Settings

DIMENSION_TABLES: Final[tuple[str, ...]] = (
    "clientes",
    "destinatarios",
    "productos",
    "jerarquia",
)
_IDENTIFIER = re.compile(r"^[a-z_][a-z0-9_]*$")


def _identifier(value: str) -> str:
    if not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def _utc_timestamp(value: datetime) -> pd.Timestamp:
    """Normalize naive and timezone-aware database values for safe comparison."""
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def create_neon_engine(settings: Settings) -> Engine:
    """Create a pooled SQLAlchemy engine without logging its URL."""
    database_url = settings.require_database_url()
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
    return create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 20},
    )


def read_watermark(engine: Engine, settings: Settings) -> datetime | None:
    schema = _identifier(settings.control_schema)
    query = text(
        f"SELECT last_processed_at FROM {schema}.pipeline_watermarks "
        "WHERE pipeline_name = :pipeline_name"
    )
    with engine.connect() as connection:
        value = connection.execute(
            query, {"pipeline_name": settings.pipeline_name}
        ).scalar_one_or_none()
    return value


def extract_dimensions(engine: Engine, settings: Settings) -> dict[str, pd.DataFrame]:
    """Extract the four small dimensions in full."""
    schema = _identifier(settings.source_schema)
    frames: dict[str, pd.DataFrame] = {}
    with engine.connect() as connection:
        for table in DIMENSION_TABLES:
            safe_table = _identifier(table)
            frames[table] = pd.read_sql_query(
                text(f"SELECT * FROM {schema}.{safe_table}"),
                connection,
            )
    return frames


def extract_sales(
    engine: Engine,
    settings: Settings,
    watermark: datetime | None,
) -> pd.DataFrame:
    """Extract all sales initially and only newer rows on later runs."""
    schema = _identifier(settings.source_schema)
    where_clause = ""
    parameters: dict[str, datetime] = {}
    if watermark is not None:
        where_clause = "WHERE ts_movimiento > :last_processed_at"
        parameters["last_processed_at"] = watermark
    query = text(
        f"SELECT * FROM {schema}.ventas {where_clause} "
        "ORDER BY ts_movimiento, nu_factura, nu_item_factura"
    )
    with engine.connect() as connection:
        return pd.read_sql_query(query, connection, params=parameters)


def max_sales_watermark(sales: pd.DataFrame) -> datetime | None:
    """Return the candidate watermark without modifying database state."""
    if sales.empty or "ts_movimiento" not in sales:
        return None
    value = pd.to_datetime(sales["ts_movimiento"], errors="raise").max()
    return value.to_pydatetime()


def update_watermark(
    engine: Engine,
    settings: Settings,
    candidate: datetime,
) -> None:
    """Advance the watermark atomically after all pipeline steps succeed."""
    schema = _identifier(settings.control_schema)
    query = text(
        f"UPDATE {schema}.pipeline_watermarks "
        "SET last_processed_at = :candidate, updated_at = CURRENT_TIMESTAMP "
        "WHERE pipeline_name = :pipeline_name "
        "AND (last_processed_at IS NULL OR last_processed_at < :candidate)"
    )
    with engine.begin() as connection:
        result = connection.execute(
            query,
            {
                "candidate": candidate,
                "pipeline_name": settings.pipeline_name,
            },
        )
        if result.rowcount == 1:
            return

        existing = connection.execute(
            text(
                f"SELECT last_processed_at FROM {schema}.pipeline_watermarks "
                "WHERE pipeline_name = :pipeline_name"
            ),
            {"pipeline_name": settings.pipeline_name},
        ).scalar_one_or_none()
        if existing is None:
            raise RuntimeError("Watermark control row does not exist")
        if _utc_timestamp(existing) < _utc_timestamp(candidate):
            raise RuntimeError("Watermark could not be advanced")
