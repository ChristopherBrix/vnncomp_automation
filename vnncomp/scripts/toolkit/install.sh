#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s installation \" \
        bash -c \\\"
            set -x
            if [ -f \\\\\\\"/home/ubuntu/anaconda3/etc/profile.d/conda.sh\\\\\\\" ]; then
                . \\\\\\\"/home/ubuntu/anaconda3/etc/profile.d/conda.sh\\\\\\\"
            else
                export PATH=\\\\\\\"/home/ubuntu/anaconda3/bin:$PATH\\\\\\\"
            fi
            cd toolkit/${script_dir} \
                && ${sudo} env SHELLOPTS=xtrace /bin/bash install_tool.sh v1 \
                && curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success \
                || curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/failure
        \\\" > >(tee logs/install.log) 2>&1 < /dev/null
    \" "