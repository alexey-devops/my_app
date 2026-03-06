module "k8s_node" {
  source = "./modules/vm"

  vm_name        = var.vm_name
  vm_cpu         = var.vm_cpu
  vm_memory      = var.vm_memory
  vm_disk        = var.vm_disk
  vm_ip          = var.vm_ip
  ssh_user       = var.ssh_user
  ssh_public_key = var.ssh_public_key
}
