#!/bin/sh

# subnet us-west-2a, specific to the AWS account.
# security group "sshonly"
aws ec2 create-network-interface --description ${user} --subnet-id subnet-0bebd3ab62946033d --groups sg-0ae97ad442c2ea17d