"""Explicit data-quality checks for source and Silver datasets."""

from __future__ import annotations

import pandas as pd


class DataQualityError(ValueError):
    """Raised when a dataset violates a required contract."""


def require_columns(frame: pd.DataFrame, columns: set[str], dataset: str) -> None:
    missing = columns - set(frame.columns)
    if missing:
        raise DataQualityError(f"{dataset} missing columns: {sorted(missing)}")


def require_unique(frame: pd.DataFrame, columns: list[str], dataset: str) -> None:
    if frame.duplicated(subset=columns).any():
        raise DataQualityError(f"{dataset} has duplicate key: {columns}")


def require_foreign_key(
    fact: pd.DataFrame,
    fact_column: str,
    dimension: pd.DataFrame,
    dimension_column: str,
    relationship: str,
) -> None:
    missing = set(fact[fact_column].dropna()) - set(dimension[dimension_column].dropna())
    if missing:
        raise DataQualityError(
            f"{relationship} has {len(missing)} orphan key(s)"
        )


def validate_sources(
    clientes: pd.DataFrame,
    destinatarios: pd.DataFrame,
    productos: pd.DataFrame,
    jerarquia: pd.DataFrame,
    ventas: pd.DataFrame,
) -> None:
    """Validate contracts that must hold before creating Silver."""
    require_columns(clientes, {"cd_numero_cliente"}, "clientes")
    require_columns(
        destinatarios, {"cd_destinatario_mercancia"}, "destinatarios"
    )
    require_columns(
        productos,
        {"cd_numero_material", "cd_jerarquia_productos"},
        "productos",
    )
    require_columns(
        jerarquia,
        {"cd_numero_material", "cd_jerarquia_completa"},
        "jerarquia",
    )
    require_columns(
        ventas,
        {
            "nu_factura",
            "nu_item_factura",
            "fc_movimiento",
            "ts_movimiento",
            "cd_solicitante",
            "cd_destinatario_mercancia",
            "cd_numero_material",
            "ct_facturada_signo",
            "vr_neto_factura_posicion_signo",
            "vr_venta_soles_sin_flete",
        },
        "ventas",
    )

    require_unique(clientes, ["cd_numero_cliente"], "clientes")
    require_unique(
        destinatarios, ["cd_destinatario_mercancia"], "destinatarios"
    )
    require_unique(productos, ["cd_numero_material"], "productos")
    require_unique(jerarquia, ["cd_numero_material"], "jerarquia")
    require_unique(ventas, ["nu_factura", "nu_item_factura"], "ventas")

    require_foreign_key(
        ventas,
        "cd_solicitante",
        clientes,
        "cd_numero_cliente",
        "ventas-clientes",
    )
    require_foreign_key(
        ventas,
        "cd_destinatario_mercancia",
        destinatarios,
        "cd_destinatario_mercancia",
        "ventas-destinatarios",
    )
    require_foreign_key(
        ventas,
        "cd_numero_material",
        productos,
        "cd_numero_material",
        "ventas-productos",
    )
    require_foreign_key(
        productos,
        "cd_numero_material",
        jerarquia,
        "cd_numero_material",
        "productos-jerarquia",
    )

    product_hierarchy = productos[
        ["cd_numero_material", "cd_jerarquia_productos"]
    ].merge(
        jerarquia[["cd_numero_material", "cd_jerarquia_completa"]],
        on="cd_numero_material",
        validate="one_to_one",
    )
    inconsistent = (
        product_hierarchy["cd_jerarquia_productos"].astype("string")
        != product_hierarchy["cd_jerarquia_completa"].astype("string")
    )
    if inconsistent.any():
        raise DataQualityError("Product and hierarchy codes are inconsistent")
