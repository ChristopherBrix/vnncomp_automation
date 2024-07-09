from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import enum
from functools import total_ordering
from typing import TYPE_CHECKING, Dict, List, Optional

from flask_login import current_user
from sqlalchemy.orm import relationship

# from utils.aws_instance import AwsInstance

from vnncomp import db
from vnncomp.utils.task_steps import (
    BenchmarkClone,
    BenchmarkCreate,
    BenchmarkGithubExport,
    BenchmarkInitialize,
    BenchmarkRun,
    TaskPause,
    ToolkitCreate,
    ToolkitGithubExport,
    ToolkitInitialize,
    ToolkitClone,
    ToolkitInstall,
    ToolkitPostInstall,
    ToolkitRun,
    ToolkitCreate,
    ToolkitInitialize,
    ToolkitClone,
    ToolkitInstall,
    ToolkitRun,
    TaskAssign,
    TaskAbortion,
    TaskFailure,
    TaskShutdown,
    TaskStep,
    TaskTimeout,
)
from vnncomp.utils.user import User


if TYPE_CHECKING:
    from vnncomp.utils.aws_instance import AwsInstance, AwsInstanceType


class Task(db.Model):
    __tablename__ = "tasks"

    _db_id = db.Column(db.Integer, primary_key=True)
    _db_type = db.Column(db.String)
    _db_aws_instance_type = db.Column(db.Integer, nullable=False)
    _db_ami = db.Column(db.String)
    _db_name = db.Column(db.String)
    _db_repository = db.Column(db.String)
    _db_hash = db.Column(db.String)
    _db_script_dir = db.Column(db.String)
    _db_steps: List[TaskStep] = relationship(
        "TaskStep", foreign_keys=[TaskStep._db_task_id], back_populates="_db_task"
    )
    _db_current_step_id = db.Column(db.Integer, db.ForeignKey("task_steps._db_id"))
    _db_current_step = relationship(
        "TaskStep", foreign_keys=[_db_current_step_id], post_update=True
    )
    _db_instance = db.relationship(
        "AwsInstance", backref="_db_task", lazy=True, uselist=False
    )
    _db_total_runtime = db.Column(db.Integer)

    __mapper_args__ = {"polymorphic_identity": "task", "polymorphic_on": _db_type}

    @property
    def id(self) -> int:
        return self._db_id

    @property
    def aws_instance_type(self) -> "AwsInstanceType":
        from vnncomp.utils.aws_instance import AwsInstanceType

        return AwsInstanceType(self._db_aws_instance_type)

    @property
    def ami(self) -> str:
        return self._db_ami

    @property
    def name(self) -> str:
        return self._db_name

    @property
    def sanitized_name(self) -> str:
        return "".join(c.lower() if c.isalnum() else "_" for c in self.name)

    @property
    def repository(self) -> str:
        return self._db_repository

    @property
    def hash(self) -> str:
        return self._db_hash

    @property
    def script_dir(self) -> str:
        return self._db_script_dir

    @property
    def current_step(self) -> TaskStep:
        return self._db_current_step

    @property
    def instance(self) -> "AwsInstance":
        return self._db_instance

    @property
    def done(self) -> bool:
        return all([step.done for step in self._db_steps])

    @property
    def total_runtime(self) -> int:
        if self.done:
            if self._db_total_runtime is None:
                return 0
            else:
                return self._db_total_runtime
        else:
            if self.instance is None:
                return 0
            else:
                return (
                    datetime.utcnow() - self.instance.creation_timestamp
                ).total_seconds()

    def __init__(
        self,
        _aws_instance_type: "AwsInstanceType",
        _ami: str,
        _name: str,
        _repository: str,
        _hash: str,
        _script_dir: str,
    ):
        self._db_aws_instance_type = _aws_instance_type.value
        self._db_ami = _ami
        self._db_name = _name
        self._db_repository = _repository
        self._db_hash = _hash
        self._db_script_dir = _script_dir
        self._db_instance = None

    def assign(self, instance: "AwsInstance"):
        assert self.aws_instance_type == instance.aws_instance_type
        assert type(self.current_step) in [TaskAssign], type(self.current_step)
        self._db_instance = instance
        db.session.commit()
        self.step_succeeded()

    def abort(self):
        assert self.current_step.can_be_aborted()
        assert not self.done
        self._abort_all_uncompleted_steps()
        TaskAbortion(self).add_to_db()
        self.update_current_step(self.current_step.next_step())
        self.current_step.execute()

    def sanitize_abort(self):
        assert self.current_step is None
        self._db_current_step = self._db_steps[0]
        db.session.commit()
        self.abort()

    def timeout(self, check_status=True):
        if check_status:
            self.current_step.status_check()
        self._abort_all_uncompleted_steps()
        TaskTimeout(self).add_to_db()
        self.update_current_step(self.current_step.next_step())
        self.current_step.execute()

    @classmethod
    def get_in_progress(cls) -> List["Task"]:
        return Task.query.filter(Task._db_steps.any(TaskStep.active))

    def step_succeeded(self, check_status=True):
        if check_status:
            self.current_step.status_check()
        self.update_current_step(self.current_step.next_step())
        if self.current_step is not None:
            self.current_step.execute()

    def _replace_next_steps_with(self, new_step: TaskStep):
        for step in self._db_steps:
            if not step.active and not step.done and not step is new_step:
                print("Deleting", step)
                db.session.delete(step)
        db.session.commit()

    def _abort_all_uncompleted_steps(self):
        for step in self._db_steps:
            if not step.done:
                step.abort()

    def step_failed(self, check_status=True):
        print("Task", self, "failed.")
        if check_status:
            self.current_step.status_check()
        if self.current_step.retry_until_success():
            self.current_step.execute()
        else:
            self._abort_all_uncompleted_steps()
            TaskFailure(self).add_to_db()
            self.update_current_step(self.current_step.next_step())
            self.current_step.execute()

    def update_logs(self, step: TaskStep):
        if not step.save_logs():
            print("Not updating logs", step)
            return

    def update_current_step(self, step: TaskStep):
        self.current_step.active = False
        self.current_step.done = True
        self._db_current_step = step
        db.session.commit()

    def force_step(self, step_id: int):
        new_active_step = None
        for step in self._db_steps:
            if step._db_id < step_id:
                step._db_aborted = False
                step.done = True
                step.active = False
            elif step._db_id == step_id:
                step._db_aborted = False
                step.done = False
                step.active = True
                self._db_current_step = step
                new_active_step = step
            else:
                assert step._db_id > step_id
                step._db_aborted = False
                step.done = False
                step.active = False
        db.session.commit()
        assert new_active_step is not None
        new_active_step.execute()

    @classmethod
    def get_all(cls) -> List["Task"]:
        return cls.query.order_by(cls._db_id).all()

    @classmethod
    def get(cls, id: int) -> "Task":
        return cls.query.get(id)


class BenchmarkTask(Task):
    __tablename__ = "benchmark_tasks"
    _db_id = db.Column(None, db.ForeignKey("tasks._db_id"), primary_key=True)
    _db_vnnlib_dir = db.Column(db.String)
    _db_onnx_dir = db.Column(db.String)
    _db_csv_file = db.Column(db.String, nullable=True)
    _db_csv_onnx_base = db.Column(db.String)
    _db_csv_vnnlib_base = db.Column(db.String)

    __mapper_args__ = {
        "polymorphic_identity": "benchmark_task",
    }

    @property
    def vnnlib_dir(self) -> str:
        return self._db_vnnlib_dir

    @property
    def onnx_dir(self) -> str:
        return self._db_onnx_dir

    @property
    def csv_file(self) -> str:
        return self._db_csv_file

    @property
    def csv_onnx_base(self) -> str:
        return self._db_csv_onnx_base

    @property
    def csv_vnnlib_base(self) -> str:
        return self._db_csv_vnnlib_base

    def __init__(
        self,
        _aws_instance_type: "AwsInstanceType",
        _name: str,
        _repository: str,
        _hash: str,
        _script_dir: str,
        _vnnlib_dir: str,
        _onnx_dir: str,
        _csv_file: str,
        _csv_onnx_base: str,
        _csv_vnnlib_base: str,
    ):
        super().__init__(
            _aws_instance_type=_aws_instance_type,
            _ami="ami-0892d3c7ee96c0bf7",
            _name=_name,
            _repository=_repository,
            _hash=_hash,
            _script_dir=_script_dir,
        )
        self._db_vnnlib_dir = _vnnlib_dir
        self._db_onnx_dir = _onnx_dir
        self._db_csv_file = _csv_file
        self._db_csv_onnx_base = _csv_onnx_base
        self._db_csv_vnnlib_base = _csv_vnnlib_base

    @classmethod
    def save_new(
        cls,
        _aws_instance_type: "AwsInstanceType",
        _name: str,
        _repository: str,
        _hash: str,
        _script_dir: str,
        _vnnlib_dir: str,
        _onnx_dir: str,
        _csv_file: str,
        _csv_onnx_base: str,
        _csv_vnnlib_base: str,
    ) -> "BenchmarkTask":
        task = BenchmarkTask(
            _aws_instance_type=_aws_instance_type,
            _name=_name,
            _repository=_repository,
            _hash=_hash,
            _script_dir=_script_dir,
            _vnnlib_dir=_vnnlib_dir,
            _onnx_dir=_onnx_dir,
            _csv_file=_csv_file,
            _csv_onnx_base=_csv_onnx_base,
            _csv_vnnlib_base=_csv_vnnlib_base,
        )

        db.session.add(task)
        db.session.commit()
        task._define_steps()
        task._db_current_step.execute()
        return task

    def _define_steps(self):
        self._db_steps = [
            BenchmarkCreate(self).add_to_db(),
            TaskAssign(self).add_to_db(),
            BenchmarkInitialize(self).add_to_db(),
            BenchmarkClone(self).add_to_db(),
            BenchmarkRun(self).add_to_db(),
        ]
        if current_user.admin:
            self._db_steps.append(BenchmarkGithubExport(self).add_to_db())
        self._db_steps.append(TaskShutdown(self).add_to_db())
        self._db_current_step = self._db_steps[0]
        db.session.commit()


class ToolkitTask(Task):
    __tablename__ = "toolkit_tasks"
    _db_id = db.Column(None, db.ForeignKey("tasks._db_id"), primary_key=True)
    _db_eni = db.Column(db.String)
    _db_yaml_config_file = db.Column(db.String)
    _db_yaml_config_content = db.Column(db.String)
    _db_post_install_tool = db.Column(db.String)
    _db_user_id = db.Column(db.Integer, db.ForeignKey("flasklogin_users.id"))
    _db_user = relationship("User", back_populates="submitted_toolkits")
    _db_run_networks = db.Column(db.String)
    _db_run_install_as_root = db.Column(db.Boolean)
    _db_run_post_install_as_root = db.Column(db.Boolean)
    _db_run_tool_as_root = db.Column(db.Boolean)

    __mapper_args__ = {
        "polymorphic_identity": "toolkit_task",
    }

    @property
    def eni(self) -> str:
        return self._db_eni

    @property
    def yaml_config_file(self) -> str:
        return self._db_yaml_config_file

    @property
    def yaml_config_content(self) -> str:
        return self._db_yaml_config_content

    @property
    def post_install_tool(self) -> str:
        return self._db_post_install_tool

    @property
    def benchmarks(self) -> List[str]:
        benchmarks = []
        for step in self._db_steps:
            if type(step) is ToolkitRun:
                benchmarks.append(step.benchmark_name)
        return benchmarks

    @property
    def run_networks(self) -> bool:
        for step in self._db_steps:
            if type(step) is ToolkitRun:
                return step.run_networks
        return False

    @property
    def pause(self) -> bool:
        for step in self._db_steps:
            if type(step) is TaskPause:
                return True
        return False

    @property
    def can_edit_post_install(self) -> bool:
        for step in self._db_steps:
            if type(step) is ToolkitPostInstall:
                return not (step.done or step.active or step.aborted)
        return False

    @property
    def user(self) -> User:
        return self._db_user

    @property
    def run_networks(self) -> str:
        return self._db_run_networks

    @property
    def run_install_as_root(self) -> bool:
        return self._db_run_install_as_root

    @property
    def run_post_install_as_root(self) -> bool:
        return self._db_run_post_install_as_root

    @property
    def run_tool_as_root(self) -> bool:
        return self._db_run_tool_as_root

    def __init__(
        self,
        _aws_instance_type: "AwsInstanceType",
        _eni: str,
        _ami: str,
        _name: str,
        _repository: str,
        _hash: str,
        _yaml_config_file: str,
        _yaml_config_content: str,
        _script_dir: str,
        _post_install_tool: str,
        _user: User,
        _run_networks: str,
        _run_install_as_root: bool,
        _run_post_install_as_root: bool,
        _run_tool_as_root: bool,
    ):
        super().__init__(
            _aws_instance_type=_aws_instance_type,
            _ami=_ami,
            _name=_name,
            _repository=_repository,
            _hash=_hash,
            _script_dir=_script_dir,
        )
        self._db_eni = _eni
        self._db_yaml_config_file = _yaml_config_file
        self._db_yaml_config_content = _yaml_config_content
        self._db_post_install_tool = _post_install_tool
        self._db_results = ""
        self._db_user = _user
        self._db_run_networks = _run_networks
        self._db_run_install_as_root = _run_install_as_root
        self._db_run_post_install_as_root = _run_post_install_as_root
        self._db_run_tool_as_root = _run_tool_as_root

    @classmethod
    def save_new(
        cls,
        _aws_instance_type: "AwsInstanceType",
        _eni: str,
        _ami: str,
        _name: str,
        _repository: str,
        _hash: str,
        _yaml_config_file: str,
        _yaml_config_content: str,
        _script_dir: str,
        _pause: bool,
        _post_install_tool: str,
        _benchmarks: List[str],
        _run_networks: str,
        _run_install_as_root: bool,
        _run_post_install_as_root: bool,
        _run_tool_as_root: bool,
        _export_results: bool,
    ) -> "ToolkitTask":
        task = ToolkitTask(
            _aws_instance_type=_aws_instance_type,
            _eni=_eni,
            _ami=_ami,
            _name=_name,
            _repository=_repository,
            _hash=_hash,
            _yaml_config_file=_yaml_config_file,
            _yaml_config_content=_yaml_config_content,
            _script_dir=_script_dir,
            _post_install_tool=_post_install_tool,
            _user=current_user,
            _run_networks=_run_networks,
            _run_install_as_root=_run_install_as_root,
            _run_post_install_as_root=_run_post_install_as_root,
            _run_tool_as_root=_run_tool_as_root,
        )

        db.session.add(task)
        db.session.commit()
        task._define_steps(
            _pause,
            _benchmarks,
            _run_networks,
            _run_install_as_root,
            _run_post_install_as_root,
            _run_tool_as_root,
            _export_results,
        )
        task._db_current_step.execute()
        return task

    def _define_steps(
        self,
        pause: bool,
        benchmarks: List[str],
        _run_networks: str,
        run_install_as_root: bool,
        run_post_install_as_root: bool,
        run_tool_as_root: bool,
        export_results: bool = False,
    ):
        self._db_steps = [
            ToolkitCreate(self).add_to_db(),
            TaskAssign(self).add_to_db(),
            ToolkitInitialize(self).add_to_db(),
            ToolkitClone(self).add_to_db(),
            ToolkitInstall(self, run_install_as_root).add_to_db(),
        ]
        if pause:
            self._db_steps.append(TaskPause(self).add_to_db())
        self._db_steps.append(
            ToolkitPostInstall(self, run_post_install_as_root).add_to_db()
        )
        for benchmark in benchmarks:
            self._db_steps.append(
                ToolkitRun(self, benchmark, _run_networks, run_tool_as_root).add_to_db()
            )
            if export_results:
                self._db_steps.append(ToolkitGithubExport(self, benchmark).add_to_db())
        self._db_steps.append(TaskShutdown(self).add_to_db())
        self._db_current_step = self._db_steps[0]
        db.session.commit()

    def set_post_install_script(self, post_install_script: str):
        self._db_post_install_tool = post_install_script
        db.session.commit()

    @classmethod
    def get_all_uservisible(cls) -> List["ToolkitTask"]:
        print(current_user, current_user.admin)
        if current_user.admin:
            return cls.query.order_by(cls._db_id).all()
        else:
            return current_user.submitted_toolkits

    @classmethod
    def get(cls, id: int) -> "ToolkitTask":
        task: ToolkitTask = ToolkitTask.query.get(id)
        if task is None:
            return None
        if current_user.admin or task._db_user == current_user:
            return task
        return None
