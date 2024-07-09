#!/bin/sh

aws ec2 run-instances \
    --image-id ${ami} \
    --count 1 \
    --instance-type ${type} \
    --key-name vnncomp \
    --block-device-mapping DeviceName=/dev/sda1,Ebs={VolumeSize=250} \
    --region us-west-2 \
    --network-interfaces "[{\"DeviceIndex\":0,\"NetworkInterfaceId\":\"${eni}\"}]"