# Cross-Sell Data Platform

Pipeline académico de Ingeniería de Datos que integra ventas desde Neon
PostgreSQL y feriados de la API pública Nager.Date. Construye un lakehouse
Bronze/Silver/Gold en Parquet y genera oportunidades explicables de cross-selling.

## Resultado validado

| Capa | Dataset principal | Registros |
|---|---|---:|
| Bronze | ventas | 432,082 |
| Silver | fact_sales | 432,082 |
| Gold | sales_summary | 201,218 |
| Gold | product_pairs | 26,457 |
| Gold | cross_sell_recommendations | 8,838 |
| Gold | customer_360 | 934 |

Las 8,838 recomendaciones cubren 904 clientes y excluyen productos que el
cliente ya compró mediante un movimiento clasificado como `sale`.

## Arquitectura

1. **Fuentes:** Neon PostgreSQL y Nager.Date.
2. **Bronze:** copia histórica inmutable, con metadatos de ingestión.
3. **Silver:** calidad, tipado, dimensiones, calendario y hecho de ventas.
4. **Gold:** agregados y reglas de afinidad con support, confidence y lift.
5. **Destino:** local o Azurite gratuitamente; Azure Blob es opcional.

La explicación completa está en
[architecture/architecture.md](architecture/architecture.md).

## Inicio rápido en Ubuntu/WSL

```bash
source .venv/bin/activate
make test
make azurite-up
python -m pipeline.main   --destination azurite   --env-file /ruta/privada/neon_cross_sell.env
```

La primera carga de un destino vacío usa `--full-refresh`. Para reconstruir
Silver y Gold desde Bronze sin duplicar Bronze se usa `--force-rebuild`.

## Incrementalidad

El campo fuente `source.ventas.ts_movimiento` es el cursor incremental. El
pipeline lee y actualiza `control.pipeline_watermarks` en Neon únicamente
después de completar todas las escrituras. Si no existen ventas nuevas, termina
sin reescribir datos. La decisión se documenta en
[ADR-0003](architecture/adr/0003-watermark-control.md).

## Comandos

```bash
make lint                    # Ruff y compilación
make test                    # Pruebas unitarias
make run-local               # Incremental hacia ./out
make run-rebuild             # Reconstruye Silver/Gold locales
make run-azurite             # Incremental hacia Azurite
make run-azurite-bootstrap   # Carga inicial completa hacia Azurite
make terraform-init          # Descarga AzureRM; no crea recursos
make terraform-validate      # Valida Terraform; no crea recursos
```

## Costos y seguridad

El flujo predeterminado usa software gratuito: Python, Neon Free, Docker,
Azurite y Terraform. No se ha ejecutado `terraform apply` y actualmente el
proyecto no creó recursos facturables en Azure. Los secretos viven fuera del
repositorio y nunca deben incorporarse a Git.

- [Runbook](documentation/RUNBOOK.md)
- [Control de costos](documentation/COST_NOTES.md)
- [Notas de seguridad](documentation/SECURITY_NOTES.md)
- [Reglas de calidad](data_contracts/expectations/dq_rules.md)
- [Diccionario de datos](documentation/DATA_DICTIONARY.md)

## Pruebas y CI

La suite cubre metadatos Bronze, Parquet Snappy, caché de feriados, configuración
de destinos, watermark, integridad referencial, devoluciones y recomendaciones.
El workflow de GitHub Actions ejecuta pruebas, lint y validación Terraform sin
usar credenciales de Azure.

Licencia MIT.
