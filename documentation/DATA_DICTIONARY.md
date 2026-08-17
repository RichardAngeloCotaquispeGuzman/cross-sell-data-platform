# Diccionario de datos

## Fuentes y Bronze

| Dataset | Grano / clave | Descripción |
|---|---|---|
| `clientes` | `cd_numero_cliente` | Maestro de clientes solicitantes. |
| `destinatarios` | `cd_destinatario_mercancia` | Maestro de puntos o destinatarios de entrega. |
| `productos` | `cd_numero_material` | Maestro comercial del producto. |
| `jerarquia` | `cd_numero_material` | Categorías jerárquicas del producto. |
| `ventas` | `nu_factura`, `nu_item_factura` | Posición individual de una factura o devolución. |
| `feriados` | `date`, `name` | Calendario festivo peruano obtenido de Nager.Date. |

Cada dataset Bronze incorpora `_ingested_at`, `_pipeline_run_id`,
`_source_system`, `_source_table`, `_extract_type` y `_watermark_value`.

## Silver

### Dimensiones

| Dataset | Clave | Uso |
|---|---|---|
| `dim_client` | `cd_numero_cliente` | Identidad y ubicación del cliente. |
| `dim_recipient` | `cd_destinatario_mercancia` | Identidad y ubicación del receptor. |
| `dim_product` | `cd_numero_material` | Producto unido con su jerarquía comercial. |
| `dim_calendar` | `date` | Año, mes, día, fin de semana y feriado. |

### `fact_sales`

Grano: una posición de factura (`nu_factura`, `nu_item_factura`).

| Campo | Significado |
|---|---|
| `fc_movimiento` | Fecha comercial normalizada. |
| `ts_movimiento` | Timestamp fuente usado para incrementalidad. |
| `cd_solicitante` | Cliente que realiza la compra. |
| `cd_destinatario_mercancia` | Destinatario del producto. |
| `cd_numero_material` | Producto facturado. |
| `ct_facturada_signo` | Cantidad con signo. |
| `vr_neto_factura_posicion_signo` | Importe neto con signo. |
| `vr_venta_soles_sin_flete` | Venta en soles sin flete. |
| `movement_type` | `sale`, `return` o `zero_value`. |
| `is_weekend`, `is_holiday` | Indicadores de calendario. |
| `client_*`, `recipient_*`, `product_*` | Atributos desnormalizados para análisis. |

## Gold

### `sales_summary`

Grano: fecha, cliente, producto y categoría. Publica `quantity`, `revenue` e
`invoice_count`, considerando únicamente movimientos `sale`.

### `product_pairs`

Grano: par no ordenado (`product_a`, `product_b`).

| Métrica | Fórmula / interpretación |
|---|---|
| `invoices_together` | Facturas distintas que contienen ambos productos. |
| `support` | facturas conjuntas / total de facturas de venta. |
| `confidence_a_to_b` | facturas conjuntas / facturas que contienen A. |
| `confidence_b_to_a` | facturas conjuntas / facturas que contienen B. |
| `lift` | support(A,B) / (support(A) × support(B)). |

Un lift mayor que 1 indica que el par aparece junto con mayor frecuencia de la
esperada si ambos productos fueran independientes.

### `cross_sell_recommendations`

Grano: cliente y producto recomendado. El producto recomendado no fue comprado
previamente por ese cliente mediante un movimiento `sale`.

| Campo | Significado |
|---|---|
| `supporting_product_id` | Producto comprado que activa la regla. |
| `recommended_product_id` | Oportunidad candidata de cross-selling. |
| `confidence` | Probabilidad empírica de la regla en las facturas históricas. |
| `lift` | Fuerza de asociación frente a independencia. |
| `score` | `confidence × lift × ln(1 + invoices_together)`. |
| `recommendation_rank` | Posición del candidato dentro del cliente. |
| `generated_at` | Timestamp UTC de generación del snapshot. |

Una oportunidad no representa una venta garantizada: es una recomendación
explicable basada en comportamiento conjunto histórico.

### `customer_360`

Grano: cliente. Contiene primera/última compra, facturas, productos distintos,
cantidad, ingresos, ticket promedio y número de recomendaciones disponibles.
