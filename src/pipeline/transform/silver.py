"""Silver transformations: typed dimensions, calendar, and integrated sales fact."""

from __future__ import annotations

import numpy as np
import pandas as pd

from pipeline.transform.quality import validate_sources

_NUMERIC_SALES_COLUMNS = (
    "ct_facturada_signo",
    "vr_neto_factura_posicion_signo",
    "vr_venta_soles_sin_flete",
)


def _selected_prefixed(
    frame: pd.DataFrame,
    key: str,
    prefix: str,
    candidates: tuple[str, ...],
) -> pd.DataFrame:
    columns = [key, *(column for column in candidates if column in frame.columns)]
    selected = frame[columns].copy()
    return selected.rename(
        columns={column: f"{prefix}{column}" for column in columns if column != key}
    )


def build_calendar(sales_dates: pd.Series, holidays: pd.DataFrame) -> pd.DataFrame:
    dates = pd.to_datetime(sales_dates, errors="raise").dt.normalize()
    if dates.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "year",
                "month",
                "day",
                "day_of_week",
                "is_weekend",
                "is_holiday",
                "holiday_name",
            ]
        )
    calendar = pd.DataFrame(
        {"date": pd.date_range(dates.min(), dates.max(), freq="D")}
    )
    calendar["year"] = calendar["date"].dt.year
    calendar["month"] = calendar["date"].dt.month
    calendar["day"] = calendar["date"].dt.day
    calendar["day_of_week"] = calendar["date"].dt.day_name()
    calendar["is_weekend"] = calendar["date"].dt.dayofweek >= 5

    holiday_lookup = holidays.copy()
    if holiday_lookup.empty:
        calendar["is_holiday"] = False
        calendar["holiday_name"] = pd.NA
        return calendar

    holiday_lookup["date"] = pd.to_datetime(
        holiday_lookup["date"], errors="raise"
    ).dt.normalize()
    name_column = "localName" if "localName" in holiday_lookup else "name"
    holiday_lookup = (
        holiday_lookup.groupby("date", as_index=False)[name_column]
        .agg(lambda names: " | ".join(sorted(set(names))))
        .rename(columns={name_column: "holiday_name"})
    )
    calendar = calendar.merge(holiday_lookup, on="date", how="left")
    calendar["is_holiday"] = calendar["holiday_name"].notna()
    return calendar


def build_silver(
    clientes: pd.DataFrame,
    destinatarios: pd.DataFrame,
    productos: pd.DataFrame,
    jerarquia: pd.DataFrame,
    ventas: pd.DataFrame,
    holidays: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Validate and build the five proposed Silver datasets."""
    validate_sources(clientes, destinatarios, productos, jerarquia, ventas)

    dim_client = clientes.drop_duplicates("cd_numero_cliente").copy()
    dim_recipient = destinatarios.drop_duplicates(
        "cd_destinatario_mercancia"
    ).copy()
    dim_product = productos.merge(
        jerarquia,
        on="cd_numero_material",
        how="inner",
        validate="one_to_one",
        suffixes=("_product", "_hierarchy"),
    )

    fact_sales = ventas.copy()
    fact_sales["fc_movimiento"] = pd.to_datetime(
        fact_sales["fc_movimiento"], errors="raise"
    ).dt.normalize()
    fact_sales["ts_movimiento"] = pd.to_datetime(
        fact_sales["ts_movimiento"], errors="raise"
    )
    for column in _NUMERIC_SALES_COLUMNS:
        fact_sales[column] = pd.to_numeric(fact_sales[column], errors="raise")

    negative = (fact_sales[list(_NUMERIC_SALES_COLUMNS)] < 0).any(axis=1)
    zero = (fact_sales[list(_NUMERIC_SALES_COLUMNS)] == 0).any(axis=1)
    fact_sales["movement_type"] = np.select(
        [negative, zero],
        ["return", "zero_value"],
        default="sale",
    )

    client_attributes = _selected_prefixed(
        clientes,
        "cd_numero_cliente",
        "client_",
        ("nm_nombre_1", "nm_cliente_2", "ds_ciudad", "cd_region", "cd_pais"),
    )
    recipient_attributes = _selected_prefixed(
        destinatarios,
        "cd_destinatario_mercancia",
        "recipient_",
        ("nm_nombre_1", "nm_cliente_2", "ds_ciudad", "cd_region", "cd_pais"),
    )
    product_attributes = _selected_prefixed(
        dim_product,
        "cd_numero_material",
        "product_",
        (
            "ds_texto_breve_material",
            "cd_tipo_material",
            "cd_grupo_mercancias",
            "nm_marca",
            "cd_jerarquia_nivel_1",
            "ds_jerarquia_nivel_1",
            "cd_jerarquia_nivel_2",
            "ds_jerarquia_nivel_2",
            "cd_jerarquia_nivel_3",
            "ds_jerarquia_nivel_3",
        ),
    )

    fact_sales = fact_sales.merge(
        client_attributes,
        left_on="cd_solicitante",
        right_on="cd_numero_cliente",
        how="left",
        validate="many_to_one",
    ).drop(columns=["cd_numero_cliente"])
    fact_sales = fact_sales.merge(
        recipient_attributes,
        on="cd_destinatario_mercancia",
        how="left",
        validate="many_to_one",
    )
    fact_sales = fact_sales.merge(
        product_attributes,
        on="cd_numero_material",
        how="left",
        validate="many_to_one",
    )

    dim_calendar = build_calendar(fact_sales["fc_movimiento"], holidays)
    fact_sales = fact_sales.merge(
        dim_calendar[["date", "is_weekend", "is_holiday", "holiday_name"]],
        left_on="fc_movimiento",
        right_on="date",
        how="left",
        validate="many_to_one",
    ).drop(columns=["date"])

    return {
        "dim_client": dim_client,
        "dim_recipient": dim_recipient,
        "dim_product": dim_product,
        "dim_calendar": dim_calendar,
        "fact_sales": fact_sales,
    }
