"""Gold analytics for explainable product affinity and cross-selling."""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np
import pandas as pd

from pipeline.config import Settings

PAIR_COLUMNS = [
    "product_a",
    "product_b",
    "invoices_together",
    "support",
    "confidence_a_to_b",
    "confidence_b_to_a",
    "lift",
]
RECOMMENDATION_COLUMNS = [
    "customer_id",
    "recommended_product_id",
    "recommendation_rank",
    "score",
    "supporting_product_id",
    "support",
    "confidence",
    "lift",
    "generated_at",
]


def build_product_pairs(fact_sales: pd.DataFrame) -> pd.DataFrame:
    positive = fact_sales.loc[
        fact_sales["movement_type"].eq("sale"),
        ["nu_factura", "cd_numero_material"],
    ].drop_duplicates()
    total_invoices = positive["nu_factura"].nunique()
    if total_invoices == 0:
        return pd.DataFrame(columns=PAIR_COLUMNS)

    product_counts = (
        positive.groupby("cd_numero_material")["nu_factura"]
        .nunique()
        .rename("product_invoice_count")
    )
    pairs = positive.merge(positive, on="nu_factura", suffixes=("_a", "_b"))
    pairs = pairs[
        pairs["cd_numero_material_a"].astype("string")
        < pairs["cd_numero_material_b"].astype("string")
    ]
    if pairs.empty:
        return pd.DataFrame(columns=PAIR_COLUMNS)

    result = (
        pairs.groupby(
            ["cd_numero_material_a", "cd_numero_material_b"],
            as_index=False,
        )["nu_factura"]
        .nunique()
        .rename(
            columns={
                "cd_numero_material_a": "product_a",
                "cd_numero_material_b": "product_b",
                "nu_factura": "invoices_together",
            }
        )
    )
    result["support"] = result["invoices_together"] / total_invoices
    count_a = result["product_a"].map(product_counts)
    count_b = result["product_b"].map(product_counts)
    result["confidence_a_to_b"] = result["invoices_together"] / count_a
    result["confidence_b_to_a"] = result["invoices_together"] / count_b
    support_a = count_a / total_invoices
    support_b = count_b / total_invoices
    result["lift"] = result["support"] / (support_a * support_b)
    return result[PAIR_COLUMNS].sort_values(
        ["invoices_together", "product_a", "product_b"],
        ascending=[False, True, True],
        ignore_index=True,
    )


def build_recommendations(
    fact_sales: pd.DataFrame,
    product_pairs: pd.DataFrame,
    settings: Settings,
    generated_at: datetime | None = None,
) -> pd.DataFrame:
    if product_pairs.empty:
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    eligible = product_pairs[
        (product_pairs["invoices_together"] >= settings.min_pair_invoices)
        & (product_pairs["support"] >= settings.min_support)
        & (product_pairs["lift"] >= settings.min_lift)
    ]
    rules_a = eligible.rename(
        columns={
            "product_a": "supporting_product_id",
            "product_b": "recommended_product_id",
            "confidence_a_to_b": "confidence",
        }
    )
    rules_b = eligible.rename(
        columns={
            "product_b": "supporting_product_id",
            "product_a": "recommended_product_id",
            "confidence_b_to_a": "confidence",
        }
    )
    rule_columns = [
        "supporting_product_id",
        "recommended_product_id",
        "invoices_together",
        "support",
        "confidence",
        "lift",
    ]
    rules = pd.concat(
        [rules_a[rule_columns], rules_b[rule_columns]],
        ignore_index=True,
    )
    rules = rules[rules["confidence"] >= settings.min_confidence]

    purchased = fact_sales.loc[
        fact_sales["movement_type"].eq("sale"),
        ["cd_solicitante", "cd_numero_material"],
    ].drop_duplicates()
    purchased = purchased.rename(
        columns={
            "cd_solicitante": "customer_id",
            "cd_numero_material": "supporting_product_id",
        }
    )
    candidates = purchased.merge(
        rules,
        on="supporting_product_id",
        how="inner",
        validate="many_to_many",
    )

    owned = purchased.rename(
        columns={"supporting_product_id": "recommended_product_id"}
    )
    candidates = candidates.merge(
        owned.assign(_already_owned=True),
        on=["customer_id", "recommended_product_id"],
        how="left",
    )
    candidates = candidates[candidates["_already_owned"].isna()].drop(
        columns="_already_owned"
    )
    if candidates.empty:
        return pd.DataFrame(columns=RECOMMENDATION_COLUMNS)

    candidates["score"] = (
        candidates["confidence"]
        * candidates["lift"]
        * np.log1p(candidates["invoices_together"])
    )
    candidates = candidates.sort_values(
        ["customer_id", "score", "recommended_product_id"],
        ascending=[True, False, True],
    ).drop_duplicates(["customer_id", "recommended_product_id"])
    candidates["recommendation_rank"] = (
        candidates.groupby("customer_id").cumcount() + 1
    )
    candidates = candidates[
        candidates["recommendation_rank"]
        <= settings.max_recommendations_per_customer
    ]
    candidates["generated_at"] = generated_at or datetime.now(timezone.utc)
    return candidates[RECOMMENDATION_COLUMNS].reset_index(drop=True)


def build_sales_summary(fact_sales: pd.DataFrame) -> pd.DataFrame:
    positive = fact_sales[fact_sales["movement_type"].eq("sale")].copy()
    category = (
        "product_ds_jerarquia_nivel_1"
        if "product_ds_jerarquia_nivel_1" in positive
        else "product_cd_grupo_mercancias"
    )
    dimensions = [
        "fc_movimiento",
        "cd_solicitante",
        "cd_numero_material",
        category,
    ]
    return (
        positive.groupby(dimensions, dropna=False, as_index=False)
        .agg(
            quantity=("ct_facturada_signo", "sum"),
            revenue=("vr_venta_soles_sin_flete", "sum"),
            invoice_count=("nu_factura", "nunique"),
        )
        .rename(
            columns={
                "fc_movimiento": "date",
                "cd_solicitante": "customer_id",
                "cd_numero_material": "product_id",
                category: "category",
            }
        )
    )


def build_customer_360(
    fact_sales: pd.DataFrame,
    recommendations: pd.DataFrame,
) -> pd.DataFrame:
    positive = fact_sales[fact_sales["movement_type"].eq("sale")].copy()
    if positive.empty:
        return pd.DataFrame()
    base = (
        positive.groupby("cd_solicitante", as_index=False)
        .agg(
            first_purchase_date=("fc_movimiento", "min"),
            last_purchase_date=("fc_movimiento", "max"),
            invoice_count=("nu_factura", "nunique"),
            products_purchased=("cd_numero_material", "nunique"),
            total_quantity=("ct_facturada_signo", "sum"),
            total_revenue=("vr_venta_soles_sin_flete", "sum"),
        )
        .rename(columns={"cd_solicitante": "customer_id"})
    )
    base["average_invoice_value"] = (
        base["total_revenue"] / base["invoice_count"]
    )
    if recommendations.empty:
        base["recommended_products_count"] = 0
        return base
    counts = (
        recommendations.groupby("customer_id")
        .size()
        .rename("recommended_products_count")
        .reset_index()
    )
    return base.merge(counts, on="customer_id", how="left").fillna(
        {"recommended_products_count": 0}
    )


def build_gold(
    fact_sales: pd.DataFrame,
    settings: Settings,
    generated_at: datetime | None = None,
) -> dict[str, pd.DataFrame]:
    pairs = build_product_pairs(fact_sales)
    recommendations = build_recommendations(
        fact_sales, pairs, settings, generated_at
    )
    return {
        "sales_summary": build_sales_summary(fact_sales),
        "product_pairs": pairs,
        "cross_sell_recommendations": recommendations,
        "customer_360": build_customer_360(fact_sales, recommendations),
    }
