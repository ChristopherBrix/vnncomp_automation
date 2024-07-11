#!/bin/sh
set -x

# Run the command 10 times or until it succeeds
for i in {1..10}; do
    sudo apt-get install -y python3 python3-pip unzip gnutls-bin && break
    echo "Failed to install packages. Retrying in 60 seconds..."
    sleep 60
done

