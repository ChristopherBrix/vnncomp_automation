#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "mkdir -p logs &&
    echo 'Packages are being updated...' > logs/initialize_instance.log
    while sudo fuser /var/{lib/{dpkg,apt/lists},cache/apt/archives}/lock >/dev/null 2>&1; do sleep 1; done &&
    env SHELLOPTS=xtrace sh -c ' \
        set -x; \
        sudo apt-get update \
            && sudo apt-get install -y python3 python3-pip unzip \
            && python3 -m pip install --upgrade pip \
            && git clone https://github.com/ChristopherBrix/vnncomp2022_benchmarks \
            && cd vnncomp2022_benchmarks \
            && ./setup.sh \
            && curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
            || curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure \
    ' >> logs/initialize_instance.log 2>&1 "