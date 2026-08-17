# Reglas de calidad de datos

Los contratos JSON versionados declaran todas las columnas y tipos lógicos de
Bronze, Silver y Gold. Se validan antes de escribir cada Parquet: una columna
faltante, inesperada o con tipo incompatible levanta `DataContractError`.

Las reglas de unicidad, integridad y negocio se ejecutan antes de construir
Silver. Toda violación hereda de `DataQualityError`, detiene la corrida y evita
que el watermark avance.

## Estructura requerida

- `clientes`: `cd_numero_cliente`.
- `destinatarios`: `cd_destinatario_mercancia`.
- `productos`: `cd_numero_material`, `cd_jerarquia_productos`.
- `jerarquia`: `cd_numero_material`, `cd_jerarquia_completa`.
- `ventas`: factura, ítem, fechas, cliente, destinatario, producto, cantidad y
  los dos importes comerciales.

## Unicidad

- Cliente: `cd_numero_cliente`.
- Destinatario: `cd_destinatario_mercancia`.
- Producto y jerarquía: `cd_numero_material`.
- Venta: clave compuesta `nu_factura`, `nu_item_factura`.

## Integridad referencial

- Toda venta debe referenciar un cliente existente.
- Toda venta debe referenciar un destinatario existente.
- Toda venta debe referenciar un producto existente.
- Todo producto debe tener jerarquía.
- `cd_jerarquia_productos` debe coincidir con `cd_jerarquia_completa`.

## Semántica Silver/Gold

- Fechas y timestamps inválidos provocan error.
- Cantidades e importes deben poder convertirse a valores numéricos.
- Algún valor negativo clasifica la fila como `return`.
- Sin negativos y con algún valor cero clasifica como `zero_value`.
- El resto se clasifica como `sale`.
- Pares, agregados y recomendaciones usan solo movimientos `sale`.
- Una recomendación nunca puede ser un producto ya comprado por el cliente.
- Los umbrales de support, confidence, lift y frecuencia se configuran por
  variables de entorno.

## Reacción ante fallos

No se descartan silenciosamente registros inválidos. La corrida falla, conserva
el watermark anterior y deja el incidente visible para corrección o reproceso.
