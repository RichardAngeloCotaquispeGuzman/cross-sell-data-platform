# Evidencia de ejecución en Azure

Fecha de verificación: 2026-08-17  
Pipeline run ID: `20260817T151548Z-65155c14`

Este documento contiene únicamente identificadores públicos de recursos y
métricas operativas. No contiene claves, connection strings, subscription IDs,
tenant IDs ni credenciales de Neon.

## Infraestructura creada con Terraform

El plan revisado indicó `3 to add, 0 to change, 0 to destroy`. El apply terminó
con `3 added, 0 changed, 0 destroyed`.

| Recurso | Valor seguro |
|---|---|
| Resource Group | `rg-cross-sell-dev` |
| Storage Account | `crosssellrcg2026` |
| Container | `lakehouse` |
| Región | `eastus2` |
| Redundancia | `Standard_LRS` |
| Acceso del container | privado |
| Blob endpoint | `https://crosssellrcg2026.blob.core.windows.net/` |

No se desplegaron máquinas virtuales, bases de datos Azure ni servicios de
cómputo permanente.

## Resultado del pipeline Azure

La ejecución inicial con destino Azure finalizó correctamente en 61.538
segundos. Todos los DataFrames fueron validados contra los contratos v2 antes de
publicarse.

| Capa | Datasets | Parquet | Registros principales |
|---|---:|---:|---|
| Bronze | 6 | 6 | ventas: 432,082; feriados: 42 |
| Silver | 5 | 5 | fact_sales: 432,082 |
| Gold | 4 | 4 | recomendaciones: 8,838 |
| Total | 15 | 15 | 28,433,426 bytes |

Conteos Gold verificados directamente desde los Parquet remotos:

| Dataset | Filas |
|---|---:|
| `sales_summary` | 201,218 |
| `product_pairs` | 26,457 |
| `cross_sell_recommendations` | 8,838 |
| `customer_360` | 934 |

Los 15 blobs se descargaron para lectura de footer y todos abrieron como Parquet
válido. Las rutas Bronze incluyen `ingestion_date=2026-08-17` y el run ID; las
rutas Silver y Gold publican el snapshot `current`.

## Calidad comprobada

- 20 pruebas automáticas aprobadas.
- Ruff y compilación Python aprobados.
- Terraform format y validate aprobados.
- Clave factura-item sin duplicados.
- Recomendaciones sin claves duplicadas ni celdas nulas.
- Productos ya comprados recomendados: 0.
- Esquemas remotos coherentes con los contratos tipados.

## Costos y apagado

La carga inicial ocupa aproximadamente 28.43 MB en Storage Standard LRS. Aunque
no existe cómputo permanente, Azure Storage puede consumir una parte pequeña del
crédito por capacidad y operaciones. El desarrollo ordinario debe continuar en
local o Azurite.

Al terminar la demostración se debe revisar un plan de destrucción y solicitar
aprobación antes de aplicarlo:

~~~bash
.venv/bin/terraform -chdir=infra/azure/terraform plan -destroy \
  -var='storage_account_name=crosssellrcg2026'
~~~

No se debe versionar `terraform.tfstate`, copiar claves en la documentación ni
actualizar la suscripción a pago por uso para este proyecto.
