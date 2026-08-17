# Azure Blob Storage con Terraform

Esta configuración declara el destino cloud para Bronze, Silver y Gold. El
desarrollo diario usa Azurite, sin costo Azure.

## Recursos declarados

Un `terraform apply` crea:

- Resource Group `rg-cross-sell-dev`;
- Storage Account `StorageV2 Standard_LRS`;
- container Blob privado `lakehouse`.

La connection string no se imprime como output ni se guarda en Git.

## Validación sin crear recursos

~~~bash
make terraform-init
make terraform-validate
~~~

`terraform init` descarga el proveedor y `validate` comprueba sintaxis. Ninguno
crea infraestructura.

## Plan y despliegue controlado

Autentíquese con Azure CLI y seleccione la suscripción desde su propia terminal.
No comparta IDs, códigos de dispositivo ni tokens.

~~~bash
az account show --output table
cd infra/azure/terraform
terraform plan   -var='storage_account_name=crosssellTUFIJO'   -out=/tmp/cross-sell-azure.tfplan
terraform show /tmp/cross-sell-azure.tfplan
terraform apply /tmp/cross-sell-azure.tfplan
~~~

Antes de aplicar debe comprobarse que el plan indique solamente los recursos
esperados y que no haya destrucciones. Si se modifica código Terraform o pasa
mucho tiempo, se descarta conceptualmente el plan anterior y se genera uno
nuevo.

## Publicación

El archivo privado debe incluir `DATABASE_URL` y
`AZURE_STORAGE_CONNECTION_STRING`. Después:

~~~bash
make run-azure-bootstrap ENV_FILE=/ruta/privada/neon_cross_sell.env
~~~

Verifique que el container tenga prefijos `bronze/`, `silver/` y `gold/`.

## Destrucción al finalizar

La destrucción borra recursos cloud y sus blobs. Debe hacerse únicamente con
aprobación explícita y después de guardar las evidencias del proyecto:

~~~bash
cd infra/azure/terraform
terraform plan   -destroy   -var='storage_account_name=crosssellTUFIJO'   -out=/tmp/cross-sell-destroy.tfplan
terraform show /tmp/cross-sell-destroy.tfplan
terraform apply /tmp/cross-sell-destroy.tfplan
~~~

El estado Terraform local es necesario para identificar los recursos. No debe
borrarse antes de la destrucción ni versionarse en Git.
