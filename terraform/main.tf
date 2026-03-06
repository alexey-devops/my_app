module "k8s_node" {
  source = "./modules/vm"

  vm_name          = var.vm_name
  vm_template_path = var.vm_template_path
  vm_cpu           = var.vm_cpu
  vm_memory        = var.vm_memory
  vm_disk          = var.vm_disk
  ssh_user         = var.ssh_user
  ssh_public_key   = var.ssh_public_key
  ssh_password     = var.ssh_password
}
