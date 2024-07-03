#!/bin/bash

python ./create_db_file.py &> ./data/create_db_file_output.txt;

aws configure import --csv file://data/awskey.csv
aws configure set region us-west-2
mkdir /root/.ssh
cp /var/www/html/vnncomp/data/vnncomp.pem /root/.ssh/vnncomp.pem
chmod 400 /root/.ssh/vnncomp.pem

gunicorn --bind 0.0.0.0:5000 wsgi --threads 4
