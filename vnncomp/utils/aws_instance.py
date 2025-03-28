from argparse import ArgumentError
import datetime
from email.policy import default
from enum import Enum
import json
import os
import subprocess
from typing import List, Optional
from attr import dataclass
from sqlalchemy import DateTime


from vnncomp import db
from vnncomp.utils.settings import Settings
from vnncomp.utils.task import Task, ToolkitTask
from vnncomp.utils.user import User


class AwsInstanceType(Enum):
    T2MICRO = 1
    T2LARGE = 2
    P32XLARGE = 3
    M516XLARGE = 4
    G58XLARGE = 5
    UNKNOWN = 999

    def get_aws_name(self):
        mapping = {
            AwsInstanceType.T2MICRO: "t2.micro",
            AwsInstanceType.T2LARGE: "t2.large",
            AwsInstanceType.P32XLARGE: "p3.2xlarge",
            AwsInstanceType.M516XLARGE: "m5.16xlarge",
            AwsInstanceType.G58XLARGE: "g5.8xlarge",
            AwsInstanceType.UNKNOWN: "unknown",
        }
        return mapping[self]

    @classmethod
    def get_from_type(cls, type: str) -> "AwsInstanceType":
        mapping = {
            "t2.micro": AwsInstanceType.T2MICRO,
            "t2.large": AwsInstanceType.T2LARGE,
            "p3.2xlarge": AwsInstanceType.P32XLARGE,
            "m5.16xlarge": AwsInstanceType.M516XLARGE,
            "g5.8xlarge": AwsInstanceType.G58XLARGE,
        }
        return mapping.get(type, AwsInstanceType.UNKNOWN)


def _get(dir, script, params=None):
    if params is None:
        params = {}
    try:
        root_dir = os.getenv("AWS_SCRIPT_ROOT")
        stdout = subprocess.check_output(
            [os.path.join(root_dir, "scripts", dir, script)],
            env=dict(os.environ, **params),
            stderr=subprocess.STDOUT,
            timeout=15,
        ).decode("ascii", errors="ignore")
    except subprocess.CalledProcessError as exc:
        print("Status : FAIL", exc.returncode, exc.stdout, exc.stderr)
        raise AWSException(exc)
    except subprocess.TimeoutExpired as exc:
        print("Status : TIMEOUT")
        raise AWSException(exc)
    else:
        print(f"Running '{script}' with '{params}' yielded '{stdout[-1000:]}'")
        if "port 22: Connection timed out" in stdout:
            raise AWSException(script, params, stdout)
        return stdout


class AwsInstance(db.Model):
    __tablename__ = "instances"

    _db_id = db.Column(db.String, primary_key=True)
    _db_creation_timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    _db_aws_instance_type = db.Column(db.Integer, nullable=False)
    _db_ami = db.Column(db.String)
    _db_state = db.Column(db.String)
    _db_reachability = db.Column(db.String)
    _db_ip = db.Column(db.String)
    _db_task_id = db.Column(db.String, db.ForeignKey("tasks._db_id"))

    @property
    def id(self) -> int:
        return self._db_id

    @property
    def creation_timestamp(self) -> DateTime:
        return self._db_creation_timestamp

    @property
    def aws_instance_type(self) -> AwsInstanceType:
        return AwsInstanceType(self._db_aws_instance_type)

    @property
    def ami(self) -> str:
        return self._db_ami

    @property
    def state(self) -> str:
        return self._db_state

    @property
    def reachability(self) -> str:
        return self._db_reachability

    @property
    def ip(self) -> str:
        return self._db_ip

    @property
    def task(self) -> Task:
        return self._db_task

    @property
    def task(self) -> Task:
        return self._db_task

    def __init__(
        self,
        _id: int,
        _creation_timestamp: DateTime,
        _aws_instance_type: AwsInstanceType,
        _ami: str,
        _state: str,
        _reachability: str,
        _ip: str,
    ):
        self._db_id = _id
        self._db_creation_timestamp = _creation_timestamp
        self._db_aws_instance_type = _aws_instance_type.value
        self._db_ami = _ami
        self._db_state = _state
        self._db_reachability = _reachability
        self._db_ip = _ip

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self

    def is_available(self):
        return self.state == "running" and self.reachability == "ok" and self.ip != ""

    # def install(self):
    #     try:
    #         _ping(
    #             self._get_script_dir(),
    #             "install.sh",
    #             {
    #                 "script_dir": self.task.script_dir,
    #                 "benchmark_id": str(self.task.id),
    #                 "benchmark_ip": self.ip,
    #             },
    #         )
    #     except:
    #         self.task.step_failed()

    # def test(self):
    #     try:
    #         _ping(
    #             self._get_script_dir(),
    #             "test.sh",
    #             {
    #                 "script_dir": self.task.script_dir,
    #                 "benchmark_id": str(self.task.id),
    #                 "benchmark_ip": self.ip,
    #             },
    #         )
    #     except:
    #         self.task.step_failed()

    def get_logs(self, filename: str):
        try:
            return _get(
                "", "get_logs.sh", {"log_name": filename, "benchmark_ip": self.ip}
            )
        except AWSException:
            return "Error loading logs, connection timed out."

    def terminate(self):
        now = datetime.datetime.utcnow()
        duration = (now - self._db_creation_timestamp).total_seconds()
        if self.task is not None:
            self.task._db_total_runtime = int(duration)
        db.session.commit()
        # if isinstance(self.task, ToolkitTask):
        #     assert type(self.task) is ToolkitTask
        #     self.task: ToolkitTask
        #     if self.task.user.admin:
        #         return
        _get("", "terminate_instance.sh", {"id": self.id})

    @classmethod
    def get_next_available(
        cls, aws_instance_type: AwsInstanceType, ami: str
    ) -> Optional["AwsInstance"]:
        return AwsInstance.query.filter(
            (AwsInstance._db_state == "running")
            & (AwsInstance._db_reachability == "ok")
            & (AwsInstance._db_ip != "")
            & (AwsInstance._db_task_id == None)
            & (AwsInstance._db_aws_instance_type == aws_instance_type.value)
            & (AwsInstance._db_ami == ami)
        ).first()

    def __str__(self):
        return f"{self.id}: {self.aws_instance_type} {self.ip} ({self.state}, {self.reachability}) {self.task}"

    def __eq__(self, other):
        return self.id == other.id


class AwsManager:
    def __init__(self):
        self._instances: List[AwsInstance] = []
        self.update_instance_list()

    @property
    def instances(self):
        return self._instances

    @classmethod
    def update_instance_list(cls) -> None:
        stdout = _get("", "list_running_instances.sh")
        instances: List[AwsInstance] = []
        for instance in json.loads(stdout):
            state = instance["State"]["Name"]
            if state == "terminated":
                continue
            tags = dict()
            if instance["Tags"] is not None:
                for tag in instance["Tags"]:
                    tags[tag["Key"]] = tag["Value"]
            if "IgnoreForVNNComp" in tags:
                print("Ignoring instance", instance)
                continue
            db_instance: Optional[AwsInstance] = AwsInstance.query.get(instance["Id"])
            if db_instance is None:
                aws_instance_type = AwsInstanceType.get_from_type(instance["Type"])
                if aws_instance_type == AwsInstanceType.UNKNOWN:
                    print("Running instance could not be identified - will be ignored:", instance)
                    continue
                db_instance = AwsInstance(
                    _id=instance["Id"],
                    _creation_timestamp=datetime.datetime.utcnow(),
                    _aws_instance_type=aws_instance_type,
                    _ami=instance["Ami"],
                    _state=state,
                    _reachability="none",
                    _ip=instance["Ip"],
                ).save()
            else:
                db_instance._db_state = state
                db_instance._db_ip = instance["Ip"]
            instances.append(db_instance)

        if AwsInstance.query.count() > len(instances):
            for instance in AwsInstance.query.all():
                if instance not in instances:
                    print("Deleting instance", instance)
                    db.session.delete(instance)
                    db.session.commit()

        stdout = _get("", "list_instance_status.sh")
        for status in json.loads(stdout)["InstanceStatuses"]:
            for instance in instances:
                if instance.id != status["InstanceId"]:
                    continue
                instance._db_reachability = status["InstanceStatus"]["Status"]
        db.session.commit()

        for instance in instances:
            timeout_in_hours = Settings.instance_timeout()
            if (
                instance.creation_timestamp
                < datetime.datetime.utcnow() - datetime.timedelta(hours=timeout_in_hours)
            ):
                print(f"Instance older than {timeout_in_hours} hours, terminating", instance)
                if (
                    instance.task is not None
                    and instance.creation_timestamp
                    > datetime.datetime.utcnow()
                    - datetime.timedelta(hours=timeout_in_hours, minutes=10)
                ):
                    instance.task.timeout()
                else:
                    instance.terminate()

            if (
                instance.creation_timestamp
                < datetime.datetime.utcnow() - datetime.timedelta(minutes=15)
                and instance.task is None
            ):
                print(
                    "Instance older than 15 minutes and no task is assigned, "
                    "terminating",
                    instance,
                )
                instance.terminate()

        print("Updated instance list", [str(i) for i in instances])

    @classmethod
    def start_new_toolkit_instance(cls, type: AwsInstanceType, ami: str) -> bool:
        try:
            _get(
                "toolkit",
                "create_new_instance.sh",
                {"type": type.get_aws_name(), "ami": ami},
            )
            return True
        except AWSException:
            return False

    @classmethod
    def start_new_toolkit_instance_with_eni(cls, type: AwsInstanceType, ami: str, eni: str) -> bool:
        try:
            _get(
                "toolkit",
                "create_new_instance_with_eni.sh",
                {"type": type.get_aws_name(), "ami": ami, "eni": eni},
            )
            return True
        except AWSException:
            return False

    @classmethod
    def assign_new_eni(cls, user: User) -> bool:
        try:
            stdout = _get(
                "",
                "create_new_eni.sh",
                {"user": user.username},
            )
            json_output = json.loads(stdout)
            assert len(json_output) == 1
            mac = json_output['NetworkInterface']['MacAddress']
            network_id = json_output['NetworkInterface']['NetworkInterfaceId']
            user.mac = mac
            user.eni = network_id
            db.session.commit()
            return True
        except AWSException:
            return False

    @classmethod
    def delete_eni(cls, user: User):
        try:
            assert user.eni is not None
            _get(
                "",
                "delete_eni.sh",
                {"eni_id": user.eni},
            )
        except AWSException:
            pass
        user.mac = None
        user.eni = None
        db.session.commit()


class AWSException(Exception):
    pass
