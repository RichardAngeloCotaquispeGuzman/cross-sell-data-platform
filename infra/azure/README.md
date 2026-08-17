# Azure Blob Storage con Terraform

Esta configuración declara la infraestructura opcional para publicar las capas
Bronze, Silver y Gold en Azure Blob Storage. El flujo predeterminado del proyecto
usa Azurite y no tiene costo.

## Qué crea un `terraform apply`

- Un Resource Group.
- Un Storage Account `Standard_LRS`.
- Un contenedor Blob privado llamado `lakehouse`.

La connection string no se imprime como output ni debe guardarse en Git.

## Validación local (no crea recursos)

```bash
cd infra/azure/terraform
terraform init -backend=false
terraform fmt -check
terraform validate
```

## Despliegue futuro en Azure

`terraform plan` y `terraform apply` requieren una suscripción y autenticación
de Azure. Antes de usarlos se debe confirmar que la cuenta mantiene un límite de
gasto adecuado. Aunque la configuración minimiza costo con `Standard_LRS`, un
Storage Account real no se considera permanentemente gratuito.

El nombre del Storage Account debe ser globalmente único:

```bash
terraform plan -var='storage_account_name=crosssellTUFIJO'
```

No ejecutar `terraform apply` hasta revisar el plan y el control de costos.
