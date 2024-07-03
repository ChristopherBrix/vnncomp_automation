#!/bin/bash

if [[ -z "${AUTO_APPLY_DB_UPGRADES}" ]]; then
  echo "Set AUTO_APPLY_DB_UPGRADES to automatically apply db upgrades."
else
  flask db upgrade
  echo "Automatically applying db upgrades. To avoid this, do not set AUTO_APPLY_DB_UPGRADES"
fi

aws configure import --csv file://data/awskey.csv
aws configure set region us-west-2
mkdir /root/.ssh
cp /var/www/html/vnncomp/data/vnncomp.pem /root/.ssh/vnncomp.pem
chmod 400 /root/.ssh/vnncomp.pem

gunicorn --bind 0.0.0.0:5000 wsgi --threads 4
