# terraform/main.tf

provider "azurerm" {
  features {}
}

# 1. Connect to the perimeter already built
data "azurerm_resource_group" "rg" {
  name = "medcore-prod-swiss-rg"
}

# 2. Forge the Analytics Workspace (Required by Azure for Container Logs)
resource "azurerm_log_analytics_workspace" "law" {
  name                = "medcore-logs"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

# 3. Forge the Managed Envoy Environment
resource "azurerm_container_app_environment" "env" {
  name                       = "medcore-env"
  location                   = data.azurerm_resource_group.rg.location
  resource_group_name        = data.azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.law.id
}

# 4. Forge the Application Definition
resource "azurerm_container_app" "app" {
  name                         = "medcore-api"
  container_app_environment_id = azurerm_container_app_environment.env.id
  resource_group_name          = data.azurerm_resource_group.rg.name
  revision_mode                = "Single"

  template {
    container {
      name   = "medcore-api"
      # We use a dummy Microsoft image to establish the infrastructure. 
      # GitHub Actions will immediately overwrite this with your real code.
      image  = "mcr.microsoft.com/azuredocs/containerapps-helloworld:latest" 
      cpu    = 0.25
      memory = "0.5Gi"
    }
    # THE $0 CONSUMPTION MANDATE
    min_replicas = 0
    max_replicas = 2
  }

  ingress {
    allow_insecure_connections = false
    external_enabled           = true
    target_port                = 8080 # Aligning with your Dockerfile
    traffic_weight {
      percentage      = 100
      latest_revision = true
    }
  }
}