# Control de costos

## Estado actual

- Neon: plan gratuito del proyecto académico.
- Nager.Date: API pública gratuita.
- Python, Docker, Azurite y Terraform: herramientas gratuitas.
- Azure real: **no desplegado**.
- `terraform apply`: **no ejecutado**.

## Qué comandos no crean recursos Azure

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

No ejecutar `terraform apply` hasta:

1. Confirmar una suscripción gratuita o crédito disponible.
2. Revisar el límite de gasto y alertas en el portal.
3. Revisar el plan de Terraform completo.
4. Obtener aprobación explícita del propietario del proyecto.
5. Documentar cómo destruir los recursos al finalizar la demostración.

Una alerta presupuestaria avisa; no garantiza el bloqueo automático de cargos.
Azurite sigue siendo la opción segura para desarrollo y presentación local.
