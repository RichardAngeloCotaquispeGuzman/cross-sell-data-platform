"""Runtime validation of the versioned JSON data contracts."""

from __future__ import annotations

import json
from datetime import date, datetime
from functools import lru_cache
from numbers import Integral, Real
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_integer_dtype,
    is_numeric_dtype,
    is_string_dtype,
)

from pipeline.transform.quality import DataQualityError

CONTRACTS_DIR = Path(__file__).resolve().parents[3] / "data_contracts" / "schema"
SUPPORTED_TYPES = {
    "array",
    "boolean",
    "date",
    "integer",
    "number",
    "string",
    "timestamp",
}


class DataContractError(DataQualityError):
    """Raised when a DataFrame violates its versioned JSON contract."""


@lru_cache(maxsize=3)
def load_contract(layer: str) -> dict[str, Any]:
    """Load and cache the repository contract for a medallion layer."""
    path = CONTRACTS_DIR / f"{layer}_schema.json"
    if not path.is_file():
        raise DataContractError(f"Contract not found for layer {layer}: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _matches_type(series: pd.Series, expected: str) -> bool:
    if expected not in SUPPORTED_TYPES:
        return False

    values = series.dropna()
    if values.empty:
        return True

    if expected == "string":
        return is_string_dtype(series.dtype) or values.map(
            lambda value: isinstance(value, str)
        ).all()
    if expected == "integer":
        if is_integer_dtype(series.dtype):
            return True
        return values.map(
            lambda value: isinstance(value, Integral)
            and not isinstance(value, (bool, np.bool_))
        ).all()
    if expected == "number":
        if is_numeric_dtype(series.dtype) and not is_bool_dtype(series.dtype):
            return True
        return values.map(
            lambda value: isinstance(value, Real)
            and not isinstance(value, (bool, np.bool_))
        ).all()
    if expected == "boolean":
        return is_bool_dtype(series.dtype) or values.map(
            lambda value: isinstance(value, (bool, np.bool_))
        ).all()
    if expected == "timestamp":
        return is_datetime64_any_dtype(series.dtype) or values.map(
            lambda value: isinstance(value, (datetime, pd.Timestamp))
        ).all()
    if expected == "date":
        return is_datetime64_any_dtype(series.dtype) or values.map(
            lambda value: isinstance(value, date)
        ).all()
    if expected == "array":
        return values.map(
            lambda value: isinstance(value, (list, tuple, np.ndarray))
        ).all()
    return False


def validate_frame(frame: pd.DataFrame, layer: str, dataset: str) -> None:
    """Validate exact columns and logical types before publishing a DataFrame."""
    contract = load_contract(layer)
    datasets = contract.get("datasets", {})
    if dataset not in datasets:
        raise DataContractError(f"{layer}/{dataset} has no declared contract")

    expected_columns = datasets[dataset].get("columns", {})
    missing = set(expected_columns) - set(frame.columns)
    unexpected = set(frame.columns) - set(expected_columns)
    errors: list[str] = []

    if missing:
        errors.append(f"missing columns={sorted(missing)}")
    if not contract.get("additional_columns", True) and unexpected:
        errors.append(f"unexpected columns={sorted(unexpected)}")

    wrong_types = {
        column: {
            "expected": expected_type,
            "actual": str(frame[column].dtype),
        }
        for column, expected_type in expected_columns.items()
        if column in frame.columns
        and not _matches_type(frame[column], expected_type)
    }
    if wrong_types:
        errors.append(f"wrong types={wrong_types}")

    if errors:
        raise DataContractError(f"{layer}/{dataset}: " + "; ".join(errors))


def validate_frames(frames: dict[str, pd.DataFrame], layer: str) -> None:
    """Validate a named collection of DataFrames against one layer contract."""
    for dataset, frame in frames.items():
        validate_frame(frame, layer, dataset)
