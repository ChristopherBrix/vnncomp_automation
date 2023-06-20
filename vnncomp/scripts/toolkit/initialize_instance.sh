#!/bin/sh

scp -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem /var/www/html/vnncomp/vnncomp/scripts/toolkit/apt-get ubuntu@${benchmark_ip}:apt-get
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "mkdir -p logs &&
    echo 'Packages are being updated. This may take up to an hour...' > logs/initialize_instance.log
    sudo mv apt-get /usr/local/sbin/apt-get
    sudo chmod +x /usr/local/sbin/apt-get
    tmux new -d -s initialization \" \
        bash -c \\\"
            set -x
            wget -qO - https://apt.repos.neuron.amazonaws.com/GPG-PUB-KEY-AMAZON-AWS-NEURON.PUB | sudo apt-key add - \
            && sudo apt-get update \
            && sudo apt-get install -y python3 python3-pip unzip \
            && python3 -m pip install --upgrade pip \
            && git clone https://github.com/ChristopherBrix/vnncomp2022_benchmarks \
            && cd vnncomp2022_benchmarks \
            && ./setup.sh \
            && cd .. \
            && git clone https://github.com/ChristopherBrix/vnncomp2023_benchmarks \
            && cd vnncomp2023_benchmarks \
            && ./setup.sh \
            && cd .. \
            && curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success \
            || curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/failure
        \\\" > >(tee -a logs/initialize_instance.log) 2>&1 < /dev/null
    \" "