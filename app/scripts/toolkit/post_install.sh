#!/bin/sh

set -x
temp_file=$(mktemp)
trap "rm -f ${temp_file}" 0 2 3 15
printf "%s" "${post_install_tool}" > ${temp_file}
sed -i "s/\r$//" ${temp_file}

scp -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ${temp_file} ubuntu@${benchmark_ip}:toolkit/${script_dir}/post_install_tool.sh
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s post_installation \" \
        bash -c '
            set -x
            if [ -f \\\"/home/ubuntu/anaconda3/etc/profile.d/conda.sh\\\" ]; then
                . \\\"/home/ubuntu/anaconda3/etc/profile.d/conda.sh\\\"
            else
                export PATH=\\\"/home/ubuntu/anaconda3/bin:$PATH\\\"
            fi
            cd toolkit/${script_dir} \
                && cat post_install_tool.sh \
                && chmod +x post_install_tool.sh \
                && ${sudo} env SHELLOPTS=xtrace /bin/bash post_install_tool.sh \
                && curl --retry 2 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
                || curl --retry 2 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure
        ' > >(tee logs/post_install.log) 2>&1 < /dev/null
    \" "