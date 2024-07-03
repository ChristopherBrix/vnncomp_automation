import os.path
import datetime

from vnncomp import db
from vnncomp.main import app
from vnncomp.utils.aws_instance import AwsInstanceType
from vnncomp.utils.task import BenchmarkTask
from vnncomp.utils.user import User

if os.path.exists("/var/www/html/vnncomp/data/vnncomp.sqlite"):
    print("db file already existed.")
    exit()

with app.app_context():
    db.create_all()

    print(f'DB file was created at {datetime.datetime.now()}')
