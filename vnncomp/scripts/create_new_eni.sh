#!/bin/sh

# subnet us-west-2a, specific to the AWS account.
# security group "sshonly"
aws ec2 create-network-interface --description ${user} --subnet-id subnet-a48e22dc --groups sg-0463a6fed8f974e73