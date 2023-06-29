#!/bin/sh

aws ec2 attach-network-interface \
    --device-index 1 \
    --instance-id ${id} \
    --network-interface-id ${eni}