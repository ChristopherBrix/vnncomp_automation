from datetime import datetime

from vnncomp import db
from vnncomp.main import app
from vnncomp.utils.aws_instance import AwsInstanceType
from vnncomp.utils.task import BenchmarkTask
from vnncomp.utils.user import User

import datetime


import os.path
if not os.path.exists("/var/www/html/vnncomp/data/vnncomp.sqlite"):
    with app.app_context():
        db.create_all()



        admin_user = User()
        admin_user.username = "tim@tim.com"
        admin_user.password = "sdfsdfsdf"
        admin_user.admin = True
        admin_user.enabled = True
        admin_user.created_on = datetime.datetime.now()
        db.session.add(admin_user)
        db.session.commit()

        user1 = User()
        user1.username = "john@john.com"
        user1.password = "sdfsdfsdf"
        user1.admin = False
        user1.enabled = True
        user1.created_on = datetime.datetime.now()
        db.session.add(user1)
        db.session.commit()

        benchmark_task = BenchmarkTask.save_new(
            _aws_instance_type=AwsInstanceType.T2LARGE,
            _name="whateva",
            _repository="https://whateva",
            _hash="blabla2fe4tgwg",
            _script_dir="some/random/path",
            _vnnlib_dir="some/other/random/path",
            _onnx_dir="some/super/different/other/path",
            _csv_file="some/random/file",
            _csv_onnx_base="idk_what_this_is",
            _csv_vnnlib_base="idk_wtf_this_is",
        )
        db.session.add(benchmark_task)
        db.session.commit()


        with open("./data/somerandomfile.txt", mode='a') as file:
            file.write('DB file was created at %s.\n' % 
                    (datetime.datetime.now()))

else:
    print("db file already existed.")
