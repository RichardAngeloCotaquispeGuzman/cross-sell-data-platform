# Checklist de evaluación y evidencias

Este documento traduce la rúbrica del profesor a evidencia verificable. Se
actualizó después de la ejecución real y verificada en Azure.

## Evaluación técnica

| Criterio oficial | Peso | Estado actual | Evidencia |
|---|---:|---|---|
| Diseño de arquitectura | 20% | Cumplido | Dos diagramas Mermaid, mapeo físico, ADR, riesgos y observabilidad |
| Implementación ETL | 20% | Cumplido | Neon + API, Bronze/Silver/Gold, incrementalidad y reglas de asociación |
| Almacenamiento cloud | 15% | Cumplido | Terraform creó Storage y 15 Parquet fueron verificados directamente en Azure |
| Automatización | 10% | Cumplido | CI de `main` y workflow incremental Azure ejecutados con éxito; cron protegido |
| Calidad del código | 5% | Cumplido | Ruff, pytest, compilación y contratos v2 tipados y ejecutables |

## Evaluación conceptual

| Criterio oficial | Peso | Evidencia |
|---|---:|---|
| Justificación técnica | 15% | ADR, arquitectura, particionado, watermark y elección lakehouse |
| Claridad documental | 10% | README reproducible, diagramas, diccionario y runbook |
| Defensa de decisiones | 5% | Riesgos, alternativas productivas, costos y limitaciones |

## Criterios funcionales del proyecto

| # | Criterio | Estado | Comprobación |
|---:|---|---|---|
| 1 | Conexión con Neon | Validado | Ejecución real contra PostgreSQL |
| 2 | Extracción de cinco tablas | Validado | Cuatro dimensiones y ventas |
| 3 | API pública | Validado | Nager.Date con timeout, retry y caché |
| 4 | Bronze Parquet | Validado | Snappy, metadata, ingestion_date y run_id |
| 5 | Silver validado | Validado | PK, FK, jerarquía, fechas y números |
| 6 | Gold no vacío | Validado | 8,838 recomendaciones |
| 7 | Ejecución local reproducible | Validado | README + Make |
| 8 | Pruebas automáticas | Validado | `make test` |
| 9 | Azurite con Docker | Validado | Capas publicadas en container local |
| 10 | Loader Azure | Validado | Ejecución real: 15 Parquet y 28,433,426 bytes en Azure Blob |
| 11 | README completo | Validado | Clone, setup, operación, cloud y seguridad |
| 12 | GitHub Actions | Validado | CI + workflow manual |
| 13 | Sin secretos versionados | Validado | `.gitignore` y escaneo del repositorio |

## Evidencia Azure completada

La evidencia reproducible se encuentra en
[`AZURE_EVIDENCE.md`](AZURE_EVIDENCE.md). Incluye el apply de tres recursos,
outputs seguros, inventario de 15 blobs, conteos, contratos y postura de costos.

Pendiente únicamente para cerrar la entrega:

- Conservar una captura del crédito/costo desde el portal para la exposición.
- Revisar y aprobar el plan de destrucción al concluir la demostración.

## Comandos de verificación

~~~bash
make lint
make test
make terraform-validate
git status
gh run list --limit 5
~~~

No se deben copiar a este documento tokens, subscription IDs, tenant IDs,
connection strings ni URLs de base de datos.
