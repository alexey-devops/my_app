output "vm_ip_address" {
  description = "IP address of the deployed Kubernetes node."
  value       = module.k8s_node.vm_ip
}

output "ssh_connection_string" {
  description = "Full SSH command to connect to the node."
  value       = module.k8s_node.ssh_command
}
