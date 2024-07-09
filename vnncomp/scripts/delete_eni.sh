#!/bin/sh

# subnet us-west-2a
aws ec2 delete-network-interface --network-interface-id ${eni_id}