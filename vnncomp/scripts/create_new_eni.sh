#!/bin/sh

# subnet us-west-2a
aws ec2 create-network-interface --description ${user} --subnet-id subnet-0bebd3ab62946033d 