import json
from pathlib import Path

import pandas as pd
import pytest

from pipeline.transform.contracts import (
    SUPPORTED_TYPES,
    DataContractError,
    validate_frame,
)


def _product_pairs_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "product_a": ["A"],
            "product_b": ["B"],
            "invoices_together": [2],
            "support": [0.5],
            "confidence_a_to_b": [0.75],
            "confidence_b_to_a": [0.5],
            "lift": [1.2],
        }
    )


def test_all_contract_datasets_declare_supported_column_types():
    for path in Path("data_contracts/schema").glob("*_schema.json"):
        contract = json.loads(path.read_text(encoding="utf-8"))
        assert contract["additional_columns"] is False
        assert contract["contract_version"] == "2.0.0"
        for dataset in contract["datasets"].values():
            assert dataset["columns"]
            assert set(dataset["columns"].values()) <= SUPPORTED_TYPES
            keys = dataset.get("primary_key", dataset.get("grain", []))
            assert set(keys) <= set(dataset["columns"])


def test_contract_accepts_valid_frame():
    validate_frame(_product_pairs_frame(), "gold", "product_pairs")


def test_contract_rejects_missing_column():
    frame = _product_pairs_frame().drop(columns=["lift"])

    with pytest.raises(DataContractError, match="missing columns"):
        validate_frame(frame, "gold", "product_pairs")


def test_contract_rejects_wrong_type():
    frame = _product_pairs_frame()
    frame["invoices_together"] = ["two"]

    with pytest.raises(DataContractError, match="wrong types"):
        validate_frame(frame, "gold", "product_pairs")


def test_contract_rejects_schema_drift():
    frame = _product_pairs_frame()
    frame["new_source_column"] = "unexpected"

    with pytest.raises(DataContractError, match="unexpected columns"):
        validate_frame(frame, "gold", "product_pairs")
