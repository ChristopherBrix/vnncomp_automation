#!/bin/sh

ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s measurements \" \
        bash -c \\\"
            set -x
            if [ -f \\\\\\\"/home/ubuntu/anaconda3/etc/profile.d/conda.sh\\\\\\\" ]; then
                . \\\\\\\"/home/ubuntu/anaconda3/etc/profile.d/conda.sh\\\\\\\"
            else
                export PATH=\\\\\\\"/home/ubuntu/anaconda3/bin:$PATH\\\\\\\"
            fi
            cd vnncomp${benchmark_year}_benchmarks \
                && git pull \
                && mkdir -p ~/logs/counterexamples/${benchmark_year}_${benchmark_name} \
                && ${sudo} env SHELLOPTS=xtrace /bin/bash run_all_categories.sh v1 ~/toolkit/${script_dir} . ~/logs/results_${benchmark_year}_${benchmark_name}.csv ~/logs/counterexamples/${benchmark_year}_${benchmark_name} ${benchmark_name} ${run_networks} \
                && sed -i \\\\\\\"s/\\\\\\\\.\\\\\\\\/benchmarks/vnncomp${benchmark_year}_benchmarks\\\\\\\\/benchmarks/g\\\\\\\" ~/logs/results_${benchmark_year}_${benchmark_name}.csv \
                && curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success \
                || curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/failure
        \\\" > >(tee logs/run_${benchmark_year}_${benchmark_name}.log) 2>&1 < /dev/null
    \" "