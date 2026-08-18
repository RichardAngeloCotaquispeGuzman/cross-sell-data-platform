# Cross-Sell Data Platform

Pipeline end-to-end de Ingeniería de Datos que integra ventas
sintéticas desde Neon PostgreSQL y feriados desde Nager.Date. Construye un
lakehouse Bronze/Silver/Gold en Parquet y genera oportunidades explicables de
cross-selling según el comportamiento histórico de los clientes.

## Resultado de negocio validado

| Capa | Dataset principal | Registros |
|---|---|---:|
| Bronze | ventas | 432,082 |
| Silver | fact_sales | 432,082 |
| Gold | sales_summary | 201,218 |
| Gold | product_pairs | 26,457 |
| Gold | cross_sell_recommendations | 8,838 |
| Gold | customer_360 | 934 |

Las 8,838 recomendaciones cubren 904 clientes. Ninguna recomienda un producto
que el cliente ya haya comprado mediante un movimiento clasificado como `sale`.

## Arquitectura lógica

~~~mermaid
flowchart LR
    N[("Neon PostgreSQL")] --> E["Extract Python<br/>watermark"]
    A["Nager.Date API"] --> E
    E --> B["Bronze<br/>inmutable y particionado"]
    B --> S["Silver<br/>calidad e integración"]
    S --> G["Gold<br/>support, confidence y lift"]
    G --> R["Oportunidades<br/>cross-selling"]
    B & S & G --> D{"local / Azurite / Azure Blob"}
    T["Terraform"] -. "crea infraestructura" .-> D
    H["GitHub Actions"] --> E
~~~

La explicación detallada, el mapeo a Azure, el flujo incremental, los riesgos y
la observabilidad están en
[`architecture/architecture.md`](architecture/architecture.md).

## Decisiones principales

- Python contiene la lógica; Neon solo conserva la fuente y el watermark.
- La extracción de ventas es incremental por `ts_movimiento`.
- Gold se recalcula con todo el historial consolidado, no solo con el incremento.
- Bronze es inmutable y se particiona por `ingestion_date` y `run_id`.
- Silver y Gold publican el snapshot vigente bajo `current`.
- Azure Blob es el destino cloud; Azurite permite desarrollar sin costo.
- Las reglas son determinísticas y explicables; no se necesita ML pagado.

## Estructura del repositorio

~~~text
.github/workflows/       CI y ejecución manual
architecture/            diagramas y decisiones ADR
data_contracts/          contratos y reglas de calidad
documentation/           runbook, costos, seguridad y diccionario
infra/azure/terraform/   infraestructura Azure
notebooks/               exploración visual reproducible
src/pipeline/            extracción, transformación, carga y orquestación
tests/                   pruebas automáticas
~~~

## Requisitos

- Ubuntu 24.04 o WSL.
- Python 3.10 o superior.
- GNU Make.
- Docker y Docker Compose para Azurite.
- Terraform y Azure CLI solo para el despliegue cloud.
- Archivo privado con `DATABASE_URL`. No se requiere credencial cloud para local
  ni Azurite.

## Clonar e instalar desde cero

~~~bash
git clone https://github.com/RichardAngeloCotaquispeGuzman/cross-sell-data-platform.git
cd cross-sell-data-platform
make setup
source .venv/bin/activate
make lint
make test
~~~

No copie credenciales al repositorio. Prepare un archivo privado fuera del
proyecto siguiendo las variables documentadas en `.env.example`:

~~~text
/ruta/privada/neon_cross_sell.env
~~~

## Primera ejecución local

Un destino vacío necesita una carga completa, aunque el watermark compartido de
Neon ya tenga un valor:

~~~bash
python -m pipeline.main   --destination local   --full-refresh   --env-file /ruta/privada/neon_cross_sell.env
~~~

Corridas posteriores:

~~~bash
make run-local ENV_FILE=/ruta/privada/neon_cross_sell.env
~~~

Si no existen movimientos nuevos, `pipeline_no_changes` es el resultado
correcto. Para reconstruir Silver y Gold desde Bronze:

~~~bash
make run-rebuild ENV_FILE=/ruta/privada/neon_cross_sell.env
~~~

## Ejecución gratuita con Docker y Azurite

~~~bash
make azurite-up
make run-azurite-bootstrap ENV_FILE=/ruta/privada/neon_cross_sell.env
make run-azurite ENV_FILE=/ruta/privada/neon_cross_sell.env
make azurite-down
~~~

Azurite implementa la API de Azure Blob localmente. Permite probar el mismo
loader sin usar el crédito de Azure.

## Capas y rutas

| Capa | Publicación | Ruta |
|---|---|---|
| Bronze | histórico inmutable | `bronze/{dataset}/ingestion_date=YYYY-MM-DD/run_id={run_id}/part-00000.parquet` |
| Silver | snapshot vigente | `silver/{dataset}/current/part-00000.parquet` |
| Gold | snapshot vigente | `gold/{dataset}/current/part-00000.parquet` |

Bronze contiene las cinco tablas de Neon y feriados. Silver publica dimensiones,
calendario y `fact_sales`. Gold publica resumen de ventas, pares, recomendaciones
y `customer_360`.

## Ciencia de datos explicable

La oportunidad se genera con reglas de asociación:

- agrupar por factura;
- eliminar el producto repetido dentro de la misma factura;
- formar pares sin importar el orden;
- calcular support, confidence en ambas direcciones y lift;
- filtrar por umbrales externos;
- excluir productos ya comprados;
- ordenar por `confidence × lift × ln(1 + invoices_together)`.

Los parámetros se configuran en el entorno y no requieren cambiar código.

## Calidad, pruebas y observabilidad

~~~bash
make lint
make test
make terraform-init
make terraform-validate
~~~

La suite cubre metadata Bronze, Snappy, particionado, caché de API, watermark,
integridad referencial, devoluciones, recomendaciones y deriva de esquema. Los
contratos JSON versionados declaran todas las columnas y tipos lógicos de Bronze,
Silver y Gold; se validan automáticamente antes de publicar cada Parquet. Los logs son líneas JSON
con timestamp UTC, nivel, `run_id`, filas, duración y stack trace ante fallos.

El CI ejecuta calidad Python y Terraform en cada push, pull request o ejecución
manual. El workflow `pipeline-controlled` puede ejecutar el pipeline mediante
GitHub Secrets. El cron está declarado, pero las corridas programadas se omiten mientras la
variable de repositorio `ENABLE_SCHEDULED_PIPELINE` no sea `true`.

## Azure con Terraform

Terraform declara:

- Resource Group;
- Storage Account `Standard_LRS`;
- container privado `lakehouse`.

Antes de crear recursos revise
[`infra/azure/README.md`](infra/azure/README.md) y
[`documentation/COST_NOTES.md`](documentation/COST_NOTES.md). El despliegue
requiere una aprobación explícita y un plan nuevo. No se debe actualizar la
suscripción a pago por uso para este proyecto.

## Seguridad y reproducibilidad

- No se versionan `.env`, claves, estados Terraform ni datos generados.
- La conexión de Neon y la connection string de Azure permanecen fuera de Git.
- GitHub Actions usa Secrets, nunca valores escritos en YAML.
- El watermark avanza únicamente después de completar todas las capas.
- Un fallo se registra y cierra la conexión sin avanzar el control.

Documentación:

- [Runbook](documentation/RUNBOOK.md)
- [Checklist de evaluación](documentation/EVALUATION_CHECKLIST.md)
- [Evidencia de ejecución Azure](documentation/AZURE_EVIDENCE.md)
- [Control de costos](documentation/COST_NOTES.md)
- [Notas de seguridad](documentation/SECURITY_NOTES.md)
- [Reglas de calidad](data_contracts/expectations/dq_rules.md)
- [Diccionario de datos](documentation/DATA_DICTIONARY.md)

Licencia MIT.
