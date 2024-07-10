#!/bin/sh

aws ec2 delete-network-interface --network-interface-id ${eni_id}