"""Command-line orchestration for the end-to-end cross-selling pipeline."""

from __future__ import annotations

import argparse
import logging
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from uuid import uuid4

import pandas as pd

from pipeline.config import Settings
from pipeline.extract.api import fetch_holidays
from pipeline.extract.database import (
    create_neon_engine,
    extract_dimensions,
    extract_sales,
    max_sales_watermark,
    read_watermark,
    update_watermark,
)
from pipeline.load.parquet import read_dataset_history, write_parquet
from pipeline.logging_conf import configure_logging
from pipeline.transform.bronze import add_ingestion_metadata
from pipeline.transform.contracts import validate_frame
from pipeline.transform.gold import build_gold
from pipeline.transform.silver import build_silver

LOGGER = logging.getLogger("cross_sell_pipeline")


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--destination",
        choices=("local", "azurite", "azure"),
        help="Override DESTINATION from the environment",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Private environment file outside the repository",
    )
    parser.add_argument(
        "--force-rebuild",
        action="store_true",
        help="Rebuild Silver and Gold from Bronze even without new sales",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Extract the full source to initialize a new destination",
    )
    return parser.parse_args(argv)


def _write_frames(
    frames: dict[str, pd.DataFrame],
    layer: str,
    run_id: str,
    settings: Settings,
    partition_date: str | None = None,
) -> list[str]:
    locations = []
    for dataset, frame in frames.items():
        validate_frame(frame, layer, dataset)
        LOGGER.info("contract_validated layer=%s dataset=%s", layer, dataset)
        locations.append(
            write_parquet(
                frame,
                layer=layer,
                dataset=dataset,
                run_id=run_id,
                settings=settings,
                partition_date=partition_date,
            )
        )
        LOGGER.info("%s/%s rows=%s", layer, dataset, len(frame))
    return locations


def _deduplicate_sales(history: pd.DataFrame) -> pd.DataFrame:
    if history.empty:
        return history
    order = [
        column
        for column in ("ts_movimiento", "_ingested_at")
        if column in history.columns
    ]
    if order:
        history = history.sort_values(order)
    return history.drop_duplicates(
        ["nu_factura", "nu_item_factura"],
        keep="last",
    ).reset_index(drop=True)


def run(argv: list[str] | None = None) -> list[str]:
    """Execute all layers and advance the watermark only after success."""
    args = _arguments(argv)
    settings = Settings.from_env(args.env_file)
    if args.destination:
        settings = replace(settings, destination=args.destination)

    configure_logging(settings.log_level)
    run_started_at = datetime.now(timezone.utc)
    timer_started_at = monotonic()
    run_id = (
        run_started_at.strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid4().hex[:8]
    )
    LOGGER.info(
        "pipeline_started run_id=%s project_env=%s destination=%s",
        run_id,
        settings.project_env,
        settings.destination,
    )

    engine = None
    try:
        engine = create_neon_engine(settings)
        current_watermark = read_watermark(engine, settings)
        dimensions = extract_dimensions(engine, settings)
        extraction_watermark = None if args.full_refresh else current_watermark
        sales_increment = extract_sales(engine, settings, extraction_watermark)
        candidate_watermark = max_sales_watermark(sales_increment)

        if sales_increment.empty and not args.force_rebuild:
            LOGGER.info("pipeline_no_changes run_id=%s rows_extracted=0", run_id)
            return []

        locations: list[str] = []
        if not sales_increment.empty:
            bronze_frames: dict[str, pd.DataFrame] = {}
            for name, frame in dimensions.items():
                bronze_frames[name] = add_ingestion_metadata(
                    frame,
                    run_id=run_id,
                    source_system="neon_postgresql",
                    source_table=name,
                    extract_type="full",
                )
            bronze_frames["ventas"] = add_ingestion_metadata(
                sales_increment,
                run_id=run_id,
                source_system="neon_postgresql",
                source_table="ventas",
                extract_type=(
                    "full" if extraction_watermark is None else "incremental"
                ),
                watermark_value=current_watermark,
            )
            locations.extend(
                _write_frames(
                    bronze_frames,
                    "bronze",
                    run_id,
                    settings,
                    partition_date=run_started_at.date().isoformat(),
                )
            )

        sales_history = _deduplicate_sales(
            read_dataset_history(
                layer="bronze",
                dataset="ventas",
                settings=settings,
            )
        )
        years = (
            pd.to_datetime(sales_history["fc_movimiento"], errors="raise")
            .dt.year.unique()
            .tolist()
        )
        holidays = fetch_holidays(
            years,
            settings,
            cache_dir=settings.output_dir / "_cache" / "holidays",
        )
        if not sales_increment.empty:
            bronze_holidays = add_ingestion_metadata(
                holidays,
                run_id=run_id,
                source_system="nager_date_api",
                source_table="public_holidays",
                extract_type="full",
            )
            locations.extend(
                _write_frames(
                    {"feriados": bronze_holidays},
                    "bronze",
                    run_id,
                    settings,
                    partition_date=run_started_at.date().isoformat(),
                )
            )

        silver = build_silver(
            dimensions["clientes"],
            dimensions["destinatarios"],
            dimensions["productos"],
            dimensions["jerarquia"],
            sales_history,
            holidays,
        )
        locations.extend(_write_frames(silver, "silver", "current", settings))

        gold = build_gold(silver["fact_sales"], settings)
        locations.extend(_write_frames(gold, "gold", "current", settings))

        if candidate_watermark is not None:
            update_watermark(engine, settings, candidate_watermark)
        LOGGER.info(
            "pipeline_succeeded run_id=%s objects=%s elapsed_seconds=%.3f",
            run_id,
            len(locations),
            monotonic() - timer_started_at,
        )
        return locations
    except Exception:
        LOGGER.exception(
            "pipeline_failed run_id=%s destination=%s elapsed_seconds=%.3f",
            run_id,
            settings.destination,
            monotonic() - timer_started_at,
        )
        raise
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    run()
