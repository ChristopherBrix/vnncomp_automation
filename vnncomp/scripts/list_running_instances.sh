#!/bin/sh

aws ec2 describe-instances \
    --query "Reservations[].Instances[].{Id:InstanceId,Type:InstanceType,Ami:ImageId,State:State,Tags:Tags,Ip:PublicIpAddress}"
