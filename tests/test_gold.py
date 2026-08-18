from datetime import datetime, timezone

import pandas as pd
import pytest

from pipeline.config import Settings
from pipeline.transform.gold import build_gold, build_product_pairs
from pipeline.transform.quality import DataQualityError, validate_sources
from pipeline.transform.silver import build_silver


def source_frames():
    clientes = pd.DataFrame(
        {
            "cd_numero_cliente": ["C1", "C2"],
            "ds_ciudad": ["Lima", "Cusco"],
        }
    )
    destinatarios = pd.DataFrame(
        {"cd_destinatario_mercancia": ["D1"], "ds_ciudad": ["Lima"]}
    )
    productos = pd.DataFrame(
        {
            "cd_numero_material": ["A", "B"],
            "cd_jerarquia_productos": ["H1", "H2"],
            "ds_texto_breve_material": ["Product A", "Product B"],
            "cd_grupo_mercancias": ["G1", "G1"],
        }
    )
    jerarquia = pd.DataFrame(
        {
            "cd_numero_material": ["A", "B"],
            "cd_jerarquia_completa": ["H1", "H2"],
            "ds_jerarquia_nivel_1": ["Category", "Category"],
        }
    )
    ventas = pd.DataFrame(
        {
            "nu_factura": ["F1", "F1", "F2", "F3"],
            "nu_item_factura": [1, 2, 1, 1],
            "fc_movimiento": ["2026-07-28"] * 4,
            "ts_movimiento": [
                "2026-07-28 10:00:00",
                "2026-07-28 10:01:00",
                "2026-07-28 11:00:00",
                "2026-07-28 12:00:00",
            ],
            "cd_solicitante": ["C1", "C1", "C2", "C2"],
            "cd_destinatario_mercancia": ["D1"] * 4,
            "cd_numero_material": ["A", "B", "A", "B"],
            "ct_facturada_signo": [1, 1, 1, -1],
            "vr_neto_factura_posicion_signo": [10, 20, 10, -20],
            "vr_venta_soles_sin_flete": [10, 20, 10, -20],
        }
    )
    holidays = pd.DataFrame(
        {"date": ["2026-07-28"], "localName": ["Fiestas Patrias"]}
    )
    return clientes, destinatarios, productos, jerarquia, ventas, holidays


def test_silver_classifies_returns_and_holidays():
    silver = build_silver(*source_frames())
    fact = silver["fact_sales"]

    assert fact["movement_type"].tolist() == ["sale", "sale", "sale", "return"]
    assert fact["is_holiday"].all()
    assert fact["holiday_name"].unique().tolist() == ["Fiestas Patrias"]


def test_quality_rejects_orphan_customer():
    frames = list(source_frames())
    frames[4] = frames[4].copy()
    frames[4].loc[0, "cd_solicitante"] = "MISSING"

    with pytest.raises(DataQualityError, match="orphan"):
        validate_sources(*frames[:5])


def test_quality_rejects_duplicate_customer_key():
    frames = list(source_frames())
    duplicate = frames[0].iloc[[0]].copy()
    frames[0] = pd.concat([frames[0], duplicate], ignore_index=True)

    with pytest.raises(DataQualityError, match="duplicate key"):
        validate_sources(*frames[:5])


def test_pairs_and_recommendations_are_explainable():
    fact = pd.DataFrame(
        {
            "nu_factura": ["I1", "I1", "I2", "I2", "I3", "I4"],
            "cd_solicitante": ["C1", "C1", "C2", "C2", "C3", "C4"],
            "cd_numero_material": ["A", "B", "A", "B", "A", "B"],
            "movement_type": ["sale"] * 6,
            "fc_movimiento": pd.to_datetime(["2026-01-01"] * 6),
            "ct_facturada_signo": [1] * 6,
            "vr_venta_soles_sin_flete": [10] * 6,
            "product_ds_jerarquia_nivel_1": ["Category"] * 6,
        }
    )
    pairs = build_product_pairs(fact)
    pair = pairs.iloc[0]

    assert pair["invoices_together"] == 2
    assert pair["support"] == pytest.approx(0.5)
    assert pair["confidence_a_to_b"] == pytest.approx(2 / 3)
    assert pair["lift"] == pytest.approx(8 / 9)

    settings = Settings(
        database_url="",
        min_pair_invoices=2,
        min_support=0,
        min_confidence=0,
        min_lift=0,
    )
    gold = build_gold(
        fact,
        settings,
        generated_at=datetime(2026, 8, 16, tzinfo=timezone.utc),
    )
    recs = gold["cross_sell_recommendations"]

    assert set(map(tuple, recs[["customer_id", "recommended_product_id"]].values)) == {
        ("C3", "B"),
        ("C4", "A"),
    }
    assert not ((recs["customer_id"] == "C1") | (recs["customer_id"] == "C2")).any()
