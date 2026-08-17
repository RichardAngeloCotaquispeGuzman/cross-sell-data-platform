# ADR-0002: Modelo Bronze/Silver/Gold en Parquet

- Estado: Aceptada
- Fecha: 2026-08-16

## Contexto

La solución debe conservar trazabilidad de origen, ofrecer datos limpios para
análisis y publicar oportunidades de cross-selling sin perder reproducibilidad.

## Decisión

Se adopta una arquitectura medallion:

- Bronze conserva extracciones inmutables por `run_id`.
- Silver publica dimensiones y hechos integrados bajo `current`.
- Gold publica agregados, pares de afinidad, recomendaciones y cliente 360 bajo
  `current`.
- Todos los datasets se escriben como Parquet con compresión Snappy.

## Consecuencias

- Bronze permite auditoría y reconstrucción.
- `current` simplifica el consumo sin mezclar snapshots anteriores.
- La deduplicación por factura e ítem protege las reconstrucciones.
- La solución actual usa un archivo por dataset, adecuado al volumen académico;
  a gran escala sería necesario particionar y compactar archivos.
