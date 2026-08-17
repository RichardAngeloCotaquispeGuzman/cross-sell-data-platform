# ADR-0003: Watermark administrado por el pipeline y persistido en Neon

- Estado: Aceptada
- Fecha: 2026-08-16

## Contexto

`source.ventas.ts_movimiento` indica cuándo ocurrió cada movimiento. El pipeline
necesita recordar hasta qué instante procesó datos sin introducir ese estado en
los archivos de negocio ni depender de memoria local.

## Decisión

La lógica incremental pertenece al código Python. Neon se usa únicamente para
persistir el estado en `control.pipeline_watermarks`, separado del esquema
`source`.

1. Python lee `last_processed_at`.
2. Extrae ventas con `ts_movimiento > last_processed_at`.
3. Escribe Bronze, Silver y Gold.
4. Solo después del éxito actualiza el watermark al máximo extraído.

La actualización es monotónica e idempotente: repetir el mismo valor es válido;
retrocederlo no lo es.

## Consecuencias

- Una falla antes del final no adelanta el cursor ni pierde datos.
- El comportamiento vive en el repositorio y es testeable.
- Varias instalaciones deben usar nombres de pipeline diferentes si requieren
  cursores independientes por destino.
- Un eventual caso con múltiples filas en el mismo timestamp necesitaría un
  cursor compuesto; para los datos actuales el timestamp es suficiente.
