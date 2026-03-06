output "vm_ip" {
  description = "The IP address of the created VM."
  value       = var.vm_ip
}

output "ssh_command" {
  description = "Command to SSH into the VM."
  value       = "ssh ${var.ssh_user}@${var.vm_ip}"
}
