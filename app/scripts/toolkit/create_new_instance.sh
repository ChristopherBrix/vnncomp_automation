#!/bin/sh

aws ec2 run-instances \
    --image-id ${ami} \
    --count 1 \
    --instance-type ${type} \
    --key-name vnncomp \
    --security-groups sshonly \
    --block-device-mapping DeviceName=/dev/sda1,Ebs={VolumeSize=250} \
    --region us-west-2