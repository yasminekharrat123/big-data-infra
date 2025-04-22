Vagrant.configure("2") do |config|
  nodes = [
    { name: "infra-node-1", ip: "192.168.56.10", port: 2222, swarm_master: true, memory: "800" },
    { name: "infra-node-2", ip: "192.168.56.11", port: 2223, swarm_manager: true, memory: "1540" },
    { name: "infra-node-3", ip: "192.168.56.12", port: 2224, swarm_manager: true, memory: "800" },
    { name: "infra-db-1", ip: "192.168.56.20", port: 2232, database: true, memory: "800" }
  ]

  nodes.each do |node|
    config.vm.define node[:name] do |vm|
      vm.vm.box = "bento/ubuntu-24.04"
      vm.vm.hostname = node[:name]

      # Set memory for this node specifically
      vm.vm.provider "virtualbox" do |vb|
        vb.memory = node[:memory]  # Set the memory based on the node's configuration
        vb.cpus = 1
      end

      vm.vm.network "public_network", ip: node[:ip]
      vm.vm.network "forwarded_port", guest: 22, host: node[:port]

      # Forward host port 8050 to VM node-1 port 80
      if node[:name] == "node-1"
        vm.vm.network "forwarded_port", guest: 80, host: 8050
        vm.vm.network "forwarded_port", guest: 8080, host: 8085
      end
      
      # Forward host port 8051 to VM node-2 port 80
      if node[:name] == "node-2"
        vm.vm.network "forwarded_port", guest: 80, host: 8051
      end

      # Provisioning steps
      vm.vm.provision "shell", inline: <<-SHELL
        sudo apt update -y
        sudo apt install -y openssh-server
        sudo systemctl enable ssh
        sudo systemctl start ssh
      SHELL
    end
  end
end