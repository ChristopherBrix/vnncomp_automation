#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "nohup env SHELLOPTS=xtrace sh -c '
        set -x
        git clone ${repository} benchmark \
            && cd benchmark \
            && git checkout ${hash} \
            && cd ${script_dir} \
            && ls generate_properties.py \
            && curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
            || curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure
    ' > logs/clone.log 2>&1 < /dev/null &"