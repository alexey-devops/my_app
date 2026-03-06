resource "virtualbox_vm" "node" {
  name     = var.vm_name
  url      = var.vm_template_path # Using full path to the .vbox file
  cpus     = var.vm_cpu
  memory   = "${var.vm_memory}mib"

  network_adapter {
    type           = "bridged"
    host_interface = "Ethernet" # ВАЖНО: Замените на имя вашего сетевого интерфейса
  }

  // This provisioner waits for the VM to be ssh-ready
  provisioner "remote-exec" {
    inline = [
      "echo 'VM is up and running'",
      "sudo sed -i 's/#PubkeyAuthentication yes/PubkeyAuthentication yes/' /etc/ssh/sshd_config",
      "sudo systemctl restart sshd"
    ]

    connection {
      type     = "ssh"
      user     = var.ssh_user
      password = var.ssh_password # Потребуется пароль для первого входа
      host     = self.network_adapter[0].ipv4_address
    }
  }

  // This provisioner injects the public key
  provisioner "remote-exec" {
    inline = [
      "mkdir -p ~/.ssh",
      "echo '${var.ssh_public_key}' >> ~/.ssh/authorized_keys",
      "chmod 700 ~/.ssh",
      "chmod 600 ~/.ssh/authorized_keys"
    ]

    connection {
      type     = "ssh"
      user     = var.ssh_user
      password = var.ssh_password
      host     = self.network_adapter[0].ipv4_address
    }
  }
}
