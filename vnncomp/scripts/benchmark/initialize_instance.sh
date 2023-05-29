#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "mkdir -p logs &&
    env SHELLOPTS=xtrace sh -c ' \
        set -x; \
        sudo apt-get update \
            && sudo fallocate -l 10G /swapfile \
            && sudo chmod 600 /swapfile \
            && sudo mkswap /swapfile \
            && sudo swapon /swapfile \
            && sudo apt-get install -y python3 python3-pip unzip git-lfs \
            && sudo python3 -m pip install --upgrade pip \
            && sudo python3 -m pip install torch==1.10.2 tensorflow==2.8.0 torchvision==0.11.3 onnxruntime==1.10.0 matplotlib==3.5.1 mxnet==1.9.1 opencv-python==4.7.0.72 \
            && sudo python3 -m pip freeze \
            && git clone https://github.com/stanleybak/simple_adversarial_generator.git randgen \
            && cd randgen \
            && git checkout 34682c72681b8185ea5e448af22cb5dd3652b504 \
            && cd vnncomp_scripts \
            && sudo ./install_tool.sh v1 \
            && sudo python3 -m pip install protobuf==3.20.0 \
            && curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
            || curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure \
    ' > logs/initialize_instance.log 2>&1 "
