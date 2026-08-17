# Notas de seguridad

## Secretos

- La URL de Neon y cualquier connection string viven fuera del repositorio.
- `Settings` oculta esos campos en su representación y los logs no los imprimen.
- `.env`, credenciales, claves, estados Terraform y datos generados están
  protegidos mediante `.gitignore`.
- `.terraform.lock.hcl` sí se conserva: fija versiones y no contiene secretos.

## Almacenamiento

- Azurite escucha localmente para desarrollo.
- El contenedor Azure declarado por Terraform es privado.
- Se bloquea el acceso público por objeto y se exige TLS 1.2 como mínimo.
- La connection string no se declara como output de Terraform.

## Base de datos

- El código usa consultas parametrizadas para valores.
- Los nombres de esquema y tabla pasan una validación estricta de identificador.
- El pipeline escribe únicamente metadatos en el esquema `control`; los datos
  fuente de `source` se leen y no se modifican.

## GitHub Actions

El workflow no necesita secretos de Neon ni Azure: ejecuta pruebas unitarias,
lint, compilación y `terraform validate`. No debe añadirse una ejecución del
pipeline real a CI sin un diseño explícito de credenciales y ambientes.

## Respuesta ante exposición

Si un secreto aparece en un commit o captura, se debe revocar/rotar primero y
luego limpiar el historial. Borrar solamente el archivo no invalida la clave.
