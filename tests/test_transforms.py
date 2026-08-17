from datetime import datetime, timezone

import pandas as pd
import pyarrow.parquet as pq

from pipeline.config import Settings
from pipeline.load.parquet import read_dataset_history, write_parquet
from pipeline.transform.bronze import add_ingestion_metadata


def test_bronze_metadata_does_not_mutate_source():
    source = pd.DataFrame({"id": [1, 2]})
    enriched = add_ingestion_metadata(
        source,
        run_id="run-123",
        source_system="neon",
        source_table="clientes",
        extract_type="full",
        ingested_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )

    assert list(source.columns) == ["id"]
    assert enriched["_pipeline_run_id"].unique().tolist() == ["run-123"]
    assert enriched["_source_table"].unique().tolist() == ["clientes"]
    assert enriched["_extract_type"].unique().tolist() == ["full"]


def test_local_writer_creates_partitioned_snappy_parquet(tmp_path):
    settings = Settings(database_url="", output_dir=tmp_path)
    frame = pd.DataFrame({"customer_id": ["C1"], "score": [1.5]})

    location = write_parquet(
        frame,
        layer="bronze",
        dataset="recommendations",
        run_id="run-1",
        settings=settings,
        partition_date="2026-08-17",
    )

    assert "ingestion_date=2026-08-17/run_id=run-1" in location
    parquet_file = pq.ParquetFile(location)
    compression = parquet_file.metadata.row_group(0).column(0).compression
    assert compression == "SNAPPY"
    assert pd.read_parquet(location).to_dict("records") == frame.to_dict("records")


def test_history_reader_supports_legacy_and_date_partitioned_layout(tmp_path):
    settings = Settings(database_url="", output_dir=tmp_path)
    write_parquet(
        pd.DataFrame({"id": [1]}),
        layer="bronze",
        dataset="ventas",
        run_id="legacy",
        settings=settings,
    )
    write_parquet(
        pd.DataFrame({"id": [2]}),
        layer="bronze",
        dataset="ventas",
        run_id="partitioned",
        settings=settings,
        partition_date="2026-08-17",
    )

    history = read_dataset_history(
        layer="bronze",
        dataset="ventas",
        settings=settings,
    )

    assert sorted(history["id"].tolist()) == [1, 2]
