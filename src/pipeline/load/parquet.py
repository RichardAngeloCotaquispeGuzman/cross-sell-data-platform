"""Parquet writer for local disk, Azurite, and optional Azure Blob Storage."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import pandas as pd

from pipeline.config import Settings


def parquet_blob_name(layer: str, dataset: str, run_id: str) -> str:
    version = "current" if run_id == "current" else f"run_id={run_id}"
    return f"{layer}/{dataset}/{version}/part-00000.parquet"


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    frame.to_parquet(buffer, engine="pyarrow", compression="snappy", index=False)
    return buffer.getvalue()


def write_parquet(
    frame: pd.DataFrame,
    *,
    layer: str,
    dataset: str,
    run_id: str,
    settings: Settings,
) -> str:
    """Write one deterministic Parquet object and return its location."""
    object_name = parquet_blob_name(layer, dataset, run_id)
    payload = _parquet_bytes(frame)

    if settings.destination == "local":
        target = settings.output_dir / object_name
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".parquet.tmp")
        temporary.write_bytes(payload)
        temporary.replace(target)
        return str(target)

    from azure.core.exceptions import ResourceExistsError
    from azure.storage.blob import BlobServiceClient

    connection_string = settings.azure_storage_connection_string
    if settings.destination == "azurite" and not connection_string:
        connection_string = "UseDevelopmentStorage=true"
    service = BlobServiceClient.from_connection_string(connection_string)
    container = service.get_container_client(settings.azure_storage_container)
    try:
        container.create_container()
    except ResourceExistsError:
        pass
    blob = container.get_blob_client(object_name)
    blob.upload_blob(payload, overwrite=True)
    return f"{settings.azure_storage_container}/{object_name}"


def read_local_parquet(
    *,
    layer: str,
    dataset: str,
    run_id: str,
    settings: Settings,
) -> pd.DataFrame:
    if settings.destination != "local":
        raise ValueError("read_local_parquet only supports local destination")
    path = Path(settings.output_dir) / parquet_blob_name(layer, dataset, run_id)
    return pd.read_parquet(path)

def read_dataset_history(
    *,
    layer: str,
    dataset: str,
    settings: Settings,
) -> pd.DataFrame:
    """Read every immutable run for a dataset from the selected destination."""
    prefix = f"{layer}/{dataset}/run_id="
    frames: list[pd.DataFrame] = []
    if settings.destination == "local":
        root = Path(settings.output_dir) / layer / dataset
        paths = sorted(root.glob("run_id=*/part-*.parquet"))
        frames = [pd.read_parquet(path) for path in paths]
    else:
        from azure.storage.blob import BlobServiceClient

        connection_string = settings.azure_storage_connection_string
        if settings.destination == "azurite" and not connection_string:
            connection_string = "UseDevelopmentStorage=true"
        service = BlobServiceClient.from_connection_string(connection_string)
        container = service.get_container_client(settings.azure_storage_container)
        for blob in container.list_blobs(name_starts_with=prefix):
            payload = container.download_blob(blob.name).readall()
            frames.append(pd.read_parquet(BytesIO(payload)))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)
