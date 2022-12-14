#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s measurements \" \
        bash -c \\\"
            set -x
            cd benchmark/${script_dir} \
                && python3 generate_properties.py 676744409 \
                && ls ${vnnlib_dir}/*.vnnlib \
                && cd ~ \
                && ls benchmark/${script_dir}/${csv_file} \
                && curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
                || curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure
        \\\" > >(tee logs/run.log) 2>&1 < /dev/null
    \" "