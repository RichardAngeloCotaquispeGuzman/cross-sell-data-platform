# ADR-0001: Azure como proveedor objetivo y Azurite para desarrollo

- Estado: Aceptada
- Fecha: 2026-08-16

## Contexto

El proyecto necesita demostrar almacenamiento cloud, infraestructura como código
y una arquitectura lakehouse, pero tiene la restricción de no depender de
aplicaciones pagadas durante el desarrollo.

## Decisión

Se selecciona Azure Blob Storage como destino cloud objetivo y Azurite como
destino predeterminado de desarrollo. Terraform con el proveedor AzureRM declara
el Resource Group, Storage Account `Standard_LRS` y contenedor privado.

## Consecuencias

- El mismo código de carga funciona con Azurite y Azure Blob.
- El desarrollo y las pruebas no generan consumo Azure.
- `terraform init` y `validate` pueden ejecutarse sin credenciales.
- Un despliegue real no se considera gratuito permanentemente y requiere una
  autorización separada después de revisar la cuenta y el límite de gasto.
- Las plantillas AWS/GCP heredadas no forman parte de la solución elegida.
