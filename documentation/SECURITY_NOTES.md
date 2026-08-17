# Notas de seguridad

## Secretos

- La URL de Neon y cualquier connection string viven fuera del repositorio.
- `Settings` oculta esos campos en su representación y los logs no los imprimen.
- `.env`, credenciales, estados Terraform y datos generados están ignorados.
- `.terraform.lock.hcl` sí se conserva: fija versiones y no contiene secretos.
- GitHub Actions referencia Secrets; nunca almacena sus valores en YAML.

## Almacenamiento

- Azurite escucha localmente para desarrollo.
- El contenedor Azure declarado por Terraform es privado.
- Se bloquea el acceso público por objeto y se exige TLS 1.2.
- La connection string no se declara como output Terraform.
- La red pública y shared key permanecen habilitadas como compromiso académico
  para ejecutar desde WSL; producción debería usar identidad administrada,
  RBAC y restricciones de red.

## Base de datos

- El código usa parámetros para los valores SQL.
- Los nombres de esquema y tabla pasan validación estricta.
- El pipeline solo escribe el watermark en `control`; `source` es de lectura.
- La conexión se cierra en `finally` incluso cuando la corrida falla.

## GitHub Actions

- `ci.yml` no usa secretos y es seguro para pull requests.
- `pipeline.yml` solo corre manualmente y usa el environment `academic-demo`.
- El cron está declarado, pero el job programado requiere la variable
  `ENABLE_SCHEDULED_PIPELINE=true`; sin ella queda omitido.
- No deben ejecutarse pipelines con secretos en pull requests de terceros.

## Logging

Los logs JSON incluyen identificadores técnicos, conteos y errores. No incluyen
`DATABASE_URL` ni connection strings. Evite imprimir objetos de configuración,
variables de entorno o respuestas completas de autenticación.

## Respuesta ante exposición

Si un secreto aparece en un commit o captura:

1. Revocar o rotar inmediatamente.
2. Revisar logs y actividad.
3. Limpiar el historial Git si corresponde.
4. Actualizar GitHub Secrets y el archivo privado.

Borrar solamente el archivo no invalida una credencial comprometida.
