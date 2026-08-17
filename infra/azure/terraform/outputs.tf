output "resource_group_name" {
  description = "Azure resource group managed by this configuration."
  value       = azurerm_resource_group.data_platform.name
}

output "storage_account_name" {
  description = "Storage account that hosts the lakehouse container."
  value       = azurerm_storage_account.data_lake.name
}

output "container_name" {
  description = "Private Blob container used by the pipeline."
  value       = azurerm_storage_container.lakehouse.name
}

output "primary_blob_endpoint" {
  description = "Blob service endpoint; this output contains no credential."
  value       = azurerm_storage_account.data_lake.primary_blob_endpoint
}
