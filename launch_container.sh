#!/bin/bash

#CMD python -m vnncomp.main

# if [ -e x.txt ]
# then
# else
python ./create_db_file.py &> ./data/create_db_file_output.txt;
# fi


# https://stackoverflow.com/questions/42245816/non-interactive-sqlite3-usage-from-bash-script
# https://askubuntu.com/questions/678915/whats-the-difference-between-and-in-bash
# sqlite3 ./data/vnncomp.sqlite <<'END_SQL' # &> db_schema.txt
# .timeout 2000
# .schema
# END_SQL

# https://stackoverflow.com/questions/38832802/sqlite3-dump-schema-into-sql-file-from-command-line
# sqlite3 ./data/vnncomp.sqlite .schema &> ./data/db_schema.txt;

# https://stackoverflow.com/questions/75675/how-do-i-dump-the-data-of-some-sqlite3-tables
# sqlite3 ./data/vnncomp.sqlite .dump &> ./data/db_data_sql.txt;

# https://stackoverflow.com/questions/75675/how-do-i-dump-the-data-of-some-sqlite3-tables
# sqlite3 ./data/vnncomp.sqlite <<'END_SQL' > ./data/db_data_csv.txt
# .mode csv
# .headers on
# .dump
# END_SQL

aws configure import --csv file://data/awskey.csv
aws configure set region us-west-2
mkdir /root/.ssh
cp /var/www/html/vnncomp/data/vnncomp.pem /root/.ssh/vnncomp.pem
chmod 400 /root/.ssh/vnncomp.pem


gunicorn --bind 0.0.0.0:5000 wsgi

# flask run --host=0.0.0.0
