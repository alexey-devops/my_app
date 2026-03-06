variable "vm_name" {
  description = "Name of the virtual machine"
  type        = string
}

variable "vm_template_uuid" {
  description = "The UUID of the template VM in VirtualBox"
  type        = string
}

variable "vm_cpu" {
  description = "Number of CPU cores for the VM"
  type        = number
}

variable "vm_memory" {
  description = "Amount of RAM in MB for the VM"
  type        = number
}

variable "vm_disk" {
  description = "Size of the disk in GB for the VM"
  type        = number
}

variable "ssh_user" {
  description = "SSH user for the VM"
  type        = string
}

variable "ssh_public_key" {
  description = "Public SSH key for accessing the VM"
  type        = string
  sensitive   = true
}

variable "ssh_password" {
  description = "SSH password for the initial connection to the VM"
  type        = string
  sensitive   = true
}
