#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "nohup env SHELLOPTS=xtrace sh -c '
        set -x
        git clone ${repository} toolkit \
            && cd toolkit \
            && git checkout ${hash} \
            && cd ${script_dir} \
            && ls install_tool.sh prepare_instance.sh run_instance.sh \
            && chmod +x install_tool.sh prepare_instance.sh run_instance.sh \
            && curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
            || curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure
    ' > logs/clone.log 2>&1 < /dev/null &"