output "vm_ip" {
  description = "The IP address of the created VM."
  value       = virtualbox_vm.node.network_adapter[0].ipv4_address
}

output "ssh_command" {
  description = "Command to SSH into the VM."
  value       = "ssh ${var.ssh_user}@${virtualbox_vm.node.network_adapter[0].ipv4_address}"
}
