variable "project_name" {
  description = "Short name used in Azure resource names and tags."
  type        = string
  default     = "cross-sell"
}

variable "environment" {
  description = "Deployment environment."
  type        = string
  default     = "dev"
}

variable "location" {
  description = "Azure region for the resource group and storage account."
  type        = string
  default     = "eastus2"
}

variable "storage_account_name" {
  description = "Globally unique name: 3-24 lowercase letters and numbers."
  type        = string

  validation {
    condition = (
      length(var.storage_account_name) >= 3 &&
      length(var.storage_account_name) <= 24 &&
      can(regex("^[a-z0-9]+$", var.storage_account_name))
    )
    error_message = "Use 3-24 lowercase letters and numbers only."
  }
}

variable "container_name" {
  description = "Private Blob container for Bronze, Silver, and Gold."
  type        = string
  default     = "lakehouse"
}
