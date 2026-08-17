# Runbook de operación

## Requisitos

- Ubuntu/WSL con Python 3.12, Make, Docker y Docker Compose.
- Entorno virtual `.venv` con dependencias instaladas.
- Archivo privado fuera del repositorio con `DATABASE_URL` o
  `NEON_DATABASE_URL`.

Nunca escriba la contraseña en el chat, README, `.env.example` o Git.

## Verificación previa

```bash
source .venv/bin/activate
docker --version
docker compose version
terraform version
make lint
make test
```

## Desarrollo gratuito con Azurite

```bash
make azurite-up
```

Carga inicial de un Azurite vacío:

```bash
python -m pipeline.main --destination azurite --full-refresh   --env-file /ruta/privada/neon_cross_sell.env
```

Corrida incremental normal:

```bash
python -m pipeline.main --destination azurite   --env-file /ruta/privada/neon_cross_sell.env
```

Si no hay ventas nuevas, el resultado correcto es `pipeline_no_changes` y no se
reescriben Parquet.

Reconstrucción de Silver/Gold desde Bronze:

```bash
python -m pipeline.main --destination azurite --force-rebuild   --env-file /ruta/privada/neon_cross_sell.env
```

## Rutas publicadas

- Bronze: `bronze/{dataset}/run_id={run_id}/part-00000.parquet`.
- Silver: `silver/{dataset}/current/part-00000.parquet`.
- Gold: `gold/{dataset}/current/part-00000.parquet`.

## Diagnóstico

1. Confirmar que Azurite está activo con `docker compose ps`.
2. Ejecutar `make test` para separar errores de código y datos.
3. Revisar el primer `DataQualityError`; no adelantar manualmente el watermark.
4. Si falló después de Bronze, corregir la causa y usar `--force-rebuild`.
5. Usar `--full-refresh` solo para inicializar un destino nuevo.

## Detención

```bash
make azurite-down
```

Esto detiene el emulador. Los blobs permanecen en `.azurite/` mientras no se
borre ese directorio.
