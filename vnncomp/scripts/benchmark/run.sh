#!/bin/sh
# WARNING: The seed here must also be specified in the webdav_uploader script!

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s measurements \" \
        bash -c \\\"
            set -x
            cd benchmark/${script_dir} \
                && python3 generate_properties.py 896832480 \
                && ls ${vnnlib_dir}/*.vnnlib \
                && cd ~ \
                && ls benchmark/${script_dir}/${csv_file} \
                && curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success \
                || (find .; curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/failure)
        \\\" > >(tee logs/run.log) 2>&1 < /dev/null
    \" "