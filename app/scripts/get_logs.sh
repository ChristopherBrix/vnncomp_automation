#!/bin/sh

# trim result to 1MB
ssh -o StrictHostKeyChecking=accept-new -i ~/.ssh/vnncomp.pem -o ConnectTimeout=10 ubuntu@${benchmark_ip} \
    "tail -c 100000 logs/${log_name} 2> /dev/null || true;" || true