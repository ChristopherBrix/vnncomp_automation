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
            && sudo apt-get install -y python3 python3-pip unzip git-lfs libgl1-mesa-glx ffmpeg libsm6 libxext6 psmisc \
            && sudo python3 -m pip install --upgrade pip \
            && sudo python3 -m pip install \
                matplotlib==3.5.1 \
                mxnet==1.9.1 \
                numpy==1.23 \
                onnx==1.14.0 \
                onnxruntime==1.15.0 \
                opencv-python==4.7.0.72 \
                pandas==2.0.2 \
                protobuf==4.23.2 \
                scipy==1.10.1 \
                skl2onnx==1.14.1 \
                tensorflow==2.8.0 \
                torch==1.10.2 \
                torchvision==0.11.3 \
                webdavclient3==3.14.6 \
            && sudo python3 -m pip freeze \
            && git clone https://github.com/stanleybak/simple_adversarial_generator.git randgen \
            && cd randgen \
            && git checkout 34682c72681b8185ea5e448af22cb5dd3652b504 \
            && cd vnncomp_scripts \
            && curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success \
            || curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/failure \
    ' > logs/initialize_instance.log 2>&1 "
# Importantly, we de not execute `sudo ./install_tool.sh v1` in `vnncomp_scripts`
# It would do nothing but install outdated pip packages