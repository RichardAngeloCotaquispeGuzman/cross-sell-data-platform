# Runbook de operación

## Requisitos

- Ubuntu/WSL con Python 3.12, Make, Docker y Docker Compose.
- Entorno virtual `.venv` con dependencias instaladas.
- Archivo privado fuera del repositorio con `DATABASE_URL` o
  `NEON_DATABASE_URL`.

Nunca escriba contraseñas, tokens o connection strings en Git, capturas o logs.

## Instalación y verificación

~~~bash
make setup
source .venv/bin/activate
docker --version
docker compose version
make lint
make test
~~~

## Primera carga de un destino

El watermark vive en Neon y puede estar avanzado aunque un destino nuevo esté
vacío. Por eso la inicialización usa `--full-refresh`:

~~~bash
python -m pipeline.main   --destination local   --full-refresh   --env-file /ruta/privada/neon_cross_sell.env
~~~

## Desarrollo gratuito con Azurite

~~~bash
make azurite-up
make run-azurite-bootstrap ENV_FILE=/ruta/privada/neon_cross_sell.env
make run-azurite ENV_FILE=/ruta/privada/neon_cross_sell.env
~~~

Si no hay ventas nuevas, el resultado correcto es `pipeline_no_changes`. No se
reescriben Parquet ni se avanza el watermark.

## Reconstrucción y backfill

Reconstrucción local de Silver/Gold desde todo Bronze:

~~~bash
make run-rebuild ENV_FILE=/ruta/privada/neon_cross_sell.env
~~~

Para inicializar otro destino con todo el origen use `--full-refresh`. Un backfill
histórico selectivo todavía no está automatizado; se documentaría con rango de
fechas y un `pipeline_name` independiente para no alterar el cursor normal.

## Rutas publicadas

- Bronze:
  `bronze/{dataset}/ingestion_date=YYYY-MM-DD/run_id={run_id}/part-00000.parquet`.
- Silver: `silver/{dataset}/current/part-00000.parquet`.
- Gold: `gold/{dataset}/current/part-00000.parquet`.

El lector Bronze admite también el layout antiguo por `run_id`.

## Logs a revisar

Los logs se escriben como JSON en la terminal o en el runner:

- `pipeline_started`: identifica `run_id` y destino.
- `bronze/dataset rows=N`: conteo publicado.
- `pipeline_no_changes`: incremental sin novedades.
- `pipeline_succeeded`: objetos y duración.
- `pipeline_failed`: error y stack trace.

`LOG_LEVEL` permite seleccionar `DEBUG`, `INFO`, `WARNING` o `ERROR`.

## Diagnóstico

1. Buscar primero `pipeline_failed` y conservar el `run_id`.
2. Confirmar Neon y la API sin imprimir credenciales.
3. Confirmar Azurite con `docker compose ps`.
4. Ejecutar `make test` para separar errores de código y datos.
5. Revisar el primer `DataQualityError`.
6. No modificar manualmente el watermark.
7. Corregir la causa y repetir la corrida. Los posibles Bronze repetidos se
   deduplican por factura-item durante la reconstrucción.

Un fallo cierra la conexión y no adelanta el watermark.

## GitHub Actions

`ci` se ejecuta en push, pull request y manualmente.

`pipeline-manual` requiere:

- Secret `NEON_DATABASE_URL`.
- Secret `AZURE_STORAGE_CONNECTION_STRING` solo para destino Azure.
- Environment `academic-demo`, donde puede configurarse aprobación.

El cron está declarado, pero el job programado se omite mientras la variable de
repositorio `ENABLE_SCHEDULED_PIPELINE` no sea `true`. Habilitarla solo después
de revisar secretos, límites de ejecución y costos.

## Azure

Validar sin crear recursos:

~~~bash
make terraform-init
make terraform-validate
~~~

Después de una aprobación explícita se genera un plan nuevo, se aplica y se
ejecuta:

~~~bash
make run-azure-bootstrap ENV_FILE=/ruta/privada/neon_cross_sell.env
~~~

La conexión de Azure debe estar dentro del archivo privado, nunca en el comando.

## Detención y limpieza

~~~bash
make azurite-down
~~~

Los blobs de Azurite permanecen en `.azurite/` mientras no se borre el directorio.
La destrucción de Azure se realiza únicamente con aprobación explícita siguiendo
`infra/azure/README.md`.
