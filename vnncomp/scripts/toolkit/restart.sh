#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s restart \" \
        bash -c \\\"
            set -x
            echo '#!/bin/bash' | sudo tee /etc/rc.local && \
            echo \\\\\\\"curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success\\\\\\\" | sudo tee -a /etc/rc.local && \
            sudo chmod a+x /etc/rc.local && \
            sudo shutdown -r now
        \\\" > >(tee -a logs/restart.log) 2>&1 < /dev/null
    \" "