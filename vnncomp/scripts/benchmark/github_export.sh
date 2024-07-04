#!/bin/sh

scp -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem /var/www/html/vnncomp/data/id_rsa ubuntu@${benchmark_ip}:/home/ubuntu/.ssh/id_rsa
scp -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem /var/www/html/vnncomp/vnncomp/scripts/benchmark/webdav_uploader.py ubuntu@${benchmark_ip}:/home/ubuntu/
scp -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem /var/www/html/vnncomp/vnncomp/scripts/benchmark/postprocess_instances_file.py ubuntu@${benchmark_ip}:/home/ubuntu/
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s saving \" \
        bash -c \\\"
            export SCIEBO_USERNAME=\\\\\\\"${sciebo_username}\\\\\\\"
            export SCIEBO_PASSWORD=\\\\\\\"${sciebo_password}\\\\\\\"
            set -x
            ssh-keyscan github.com >> ~/.ssh/known_hosts \
                && git clone git@github.com:ChristopherBrix/vnncomp2024_benchmarks.git all_benchmarks \
                && rm -rf all_benchmarks/benchmarks/${name} \
                && mkdir all_benchmarks/benchmarks/${name} all_benchmarks/benchmarks/${name}/onnx \
                && cp -r benchmark/${script_dir}/${vnnlib_dir} all_benchmarks/benchmarks/${name}/vnnlib \
                && cp benchmark/${script_dir}/${onnx_dir}/*.onnx all_benchmarks/benchmarks/${name}/onnx/ \
                && cp benchmark/${script_dir}/${csv_file} all_benchmarks/benchmarks/${name}/instances.csv \
                && cd all_benchmarks \
                && gzip benchmarks/${name}/onnx/* benchmarks/${name}/vnnlib/* \
                && python3 ../postprocess_instances_file.py benchmarks/${name}/instances.csv \
                && git config --global user.name \\\\\\\"VNN-Comp Bot\\\\\\\" \
                && git config --global user.email \\\\\\\"brix@cs.rwth-aachen.de\\\\\\\" \
                && git add benchmarks/${name} \
                && cd benchmarks \
                && find ${name}/vnnlib/* ${name}/onnx/* -type f -size +100M -exec git restore --staged \\\\\\\"{}\\\\\\\" \\\\\\\\; \
                && find ${name}/vnnlib/* ${name}/onnx/* -type f -size +100M -exec sh -c \\\\\\\"python3 ~/webdav_uploader.py -n ${name} -r vnncomp2024/{} -l {} \\\\\\\" \\\\\\\\; \
                && git pull \
                && git status \
                && git commit -m \\\\\\\"Updated ${name}\\\\\\\" -m \\\\\\\"${repository} @ ${hash}, seed ${seed}\\\\\\\" \
                && git push \
                && curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/success \
                || curl --retry 100 --retry-connrefused ${ROOT_URL}/update/${benchmark_id}/failure
        \\\" > >(tee logs/github_export.log) 2>&1 < /dev/null
    \" "