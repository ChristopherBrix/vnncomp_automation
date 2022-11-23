#!/bin/sh

aws ec2 run-instances \
    --image-id ami-0892d3c7ee96c0bf7 \
    --count 1 \
    --instance-type t2.large \
    --key-name vnncomp \
    --security-groups sshonly \
    --block-device-mapping DeviceName=/dev/sda1,Ebs={VolumeSize=100}
