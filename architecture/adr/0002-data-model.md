# ADR-0002: Modelo Bronze/Silver/Gold en Parquet

- Estado: Aceptada
- Fecha: 2026-08-16
- Actualizada: 2026-08-17

## Contexto

La solución debe conservar trazabilidad de origen, ofrecer datos limpios para
análisis y publicar oportunidades de cross-selling sin perder reproducibilidad.
El particionado por fecha de ingestión o evento permite organizar el histórico
y preparar políticas posteriores de consulta y retención.

## Decisión

Se adopta una arquitectura medallion:

- Bronze conserva extracciones inmutables bajo
  `ingestion_date=YYYY-MM-DD/run_id={run_id}`.
- Silver publica dimensiones y el hecho integrado bajo `current`.
- Gold publica agregados, pares de afinidad, recomendaciones y cliente 360 bajo
  `current`.
- Todos los datasets se escriben como Parquet con compresión Snappy.
- El lector Bronze admite el layout anterior por `run_id` para no invalidar
  corridas locales existentes.

## Consecuencias

- Bronze aplica una convención de particionado, permite auditoría y facilita una
  futura política de retención.
- `current` simplifica el consumo sin mezclar snapshots analíticos anteriores.
- La deduplicación por factura e ítem protege las reconstrucciones.
- Silver y Gold son snapshots de un archivo por dataset, adecuado al volumen
  actual. A gran escala se particionarían por fecha de evento y se aplicarían
  compactación y catálogo.
