Vagrant.configure("2") do |config|
  nodes = [
    { name: "infra-node-1", ip: "192.168.56.10", port: 2222, swarm_master: true, memory: "800" },
    { name: "infra-node-2", ip: "192.168.56.11", port: 2223, swarm_manager: true, memory: "1540" },
    { name: "infra-node-3", ip: "192.168.56.12", port: 2224, swarm_manager: true, memory: "800" },
    { name: "infra-db-1", ip: "192.168.56.20", port: 2232, database: true, memory: "800" },
    { name: "infra-bigdata-1", ip: "192.168.56.30", port: 2240, bigdata: true, memory: "2048" } 
  ]

  nodes.each do |node|
    config.vm.define node[:name] do |vm|
      vm.vm.box = "bento/ubuntu-24.04"
      vm.vm.hostname = node[:name]

      vm.vm.provider "virtualbox" do |vb|
        vb.memory = node[:memory]
        vb.cpus = node[:name] == "infra-bigdata-1" ? 2 : 1
      end

      vm.vm.network "public_network", ip: node[:ip]
      vm.vm.network "forwarded_port", guest: 22, host: node[:port]

      if node[:name] == "infra-bigdata-1"
        vm.vm.network "forwarded_port", guest: 9000, host: 9000  # NameNode HDFS port
        vm.vm.network "forwarded_port", guest: 9870, host: 9870  # NameNode Web UI
        vm.vm.network "forwarded_port", guest: 9866, host: 9866  # DataNode port
        vm.vm.network "forwarded_port", guest: 9864, host: 9864  # DataNode Web UI
      end
      
      # Forward host port 8050 to VM node-1 port 80
      if node[:name] == "infra-node-1"
        vm.vm.network "forwarded_port", guest: 80, host: 8050
        vm.vm.network "forwarded_port", guest: 8080, host: 8085
      end
      
      # Forward host port 8051 to VM node-2 port 80
      if node[:name] == "infra-node-2"
        vm.vm.network "forwarded_port", guest: 80, host: 8051
      end

      if node[:name] == "infra-node-3"
        vm.vm.network "forwarded_port", guest: 9092, host: 9092
      end

      if node[:name] == "infra-db-1"
        # Elasticsearch
        vm.vm.network "forwarded_port", guest: 9200, host: 9200 
        vm.vm.network "forwarded_port", guest: 9300, host: 9300 
      
        # InfluxDB
        vm.vm.network "forwarded_port", guest: 8086, host: 8086
        vm.vm.network "forwarded_port", guest: 8088, host: 8088
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