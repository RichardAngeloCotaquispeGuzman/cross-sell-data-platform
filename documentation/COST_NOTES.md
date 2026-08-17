# Control de costos

## Estado actual

- Neon: plan gratuito del proyecto académico.
- Nager.Date: API pública gratuita.
- Python, Docker, Azurite y Terraform: herramientas gratuitas.
- Azure real: Storage Standard LRS desplegado para la demostración.
- `terraform apply`: ejecutado el 2026-08-17 con 3 recursos creados.
- Datos publicados: 15 Parquet, aproximadamente 28.43 MB.

## Qué comandos no crean recursos Azure adicionales

- `terraform fmt`
- `terraform init -backend=false`
- `terraform validate`
- Ejecuciones con `--destination local` o `--destination azurite`

`terraform init` descarga el proveedor AzureRM, pero no autentica ni crea
infraestructura.

## Qué puede generar costo

- `terraform plan` consulta una suscripción, pero no crea recursos.
- `terraform apply` crea un Resource Group, Storage Account y contenedor.
- Almacenamiento, operaciones y transferencia de un Azure Blob real pueden
  generar consumo incluso usando `Standard_LRS`.

## Política del proyecto

El apply se ejecutó después de confirmar el crédito disponible, revisar el plan
`3 to add, 0 to change, 0 to destroy` y obtener aprobación. No se desplegó
cómputo permanente.

A partir de ahora:

1. Desarrollar normalmente en local o Azurite.
2. Usar Azure solo para demostraciones controladas.
3. Revisar Crédito y Administración de costos en el portal.
4. No actualizar la suscripción a pago por uso.
5. Preparar y aprobar un plan de destrucción al finalizar la demostración.

Una alerta presupuestaria avisa; no garantiza el bloqueo automático de cargos.
Azurite sigue siendo la opción segura para desarrollo y presentación local.
