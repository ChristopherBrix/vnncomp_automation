#!/bin/sh

scp -i ~/.ssh/vnncomp.pem /home/ubuntu/.ssh/id_rsa ubuntu@${benchmark_ip}:/home/ubuntu/.ssh/id_rsa
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem ubuntu@${benchmark_ip} \
    "tmux new -d -s saving \" \
        bash -c \\\"
            set -x
            ssh-keyscan github.com >> ~/.ssh/known_hosts \
                && rm -rf all_results \
                && git clone git@github.com:ChristopherBrix/vnncomp2022_results.git all_results \
                && rm -rf all_results/${tool_name}/${benchmark_name} \
                && mkdir -p all_results/${tool_name}/${benchmark_name} \
                && touch all_results/${tool_name}/${benchmark_name}/.gitkeep
            cp logs/counterexamples/${benchmark_name}/* all_results/${tool_name}/${benchmark_name}/
            cp logs/results_${benchmark_name}.csv all_results/${tool_name}/${benchmark_name}/results.csv \
                && cd all_results
            gzip ${tool_name}/${benchmark_name}/*.counterexample
            ./merge_results_per_team.sh
            git config --global user.name \\\\\\\"VNN-Comp Bot\\\\\\\" \
                && git config --global user.email \\\\\\\"brix@cs.rwth-aachen.de\\\\\\\" \
                && git add ${tool_name}/${benchmark_name} \
                && git add ${tool_name}/results.csv \
                && git pull \
                && git status \
                && git commit -m \\\\\\\"Added results for ${tool_name} on ${benchmark_name}\\\\\\\" \
                && git push \
                && curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/success \
                || curl --retry 100 --retry-connrefused https://vnncomp.christopher-brix.de/update/${benchmark_id}/failure
        \\\" > >(tee logs/github_export_${benchmark_name}.log) 2>&1 < /dev/null
    \" "