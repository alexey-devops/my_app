terraform {
  required_version = ">= 1.0"

  required_providers {
    null = {
      source  = "hashicorp/null"
      version = ">= 3.0"
    }
    # Placeholder for a real provider
    # proxmox = {
    #   source  = "telmate/proxmox"
    #   version = "2.9.14"
    # }
  }
}
