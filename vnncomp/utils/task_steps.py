from abc import ABC, abstractmethod
from enum import Enum
from functools import total_ordering
import os
import subprocess
from typing import Dict, List, Optional, TYPE_CHECKING
from flask import url_for

from sqlalchemy.orm import relationship

from vnncomp import db

if TYPE_CHECKING:
    from vnncomp.utils.aws_instance import AwsInstance
    from vnncomp.utils.task import Task


def _ping(dir, script, params=None):
    if params is None:
        params = {}
    root_dir = os.getenv("AWS_SCRIPT_ROOT")
    print("pinging", [os.path.join(root_dir, "scripts", dir, script)])
    _ = subprocess.Popen(
        [os.path.join(root_dir, "scripts", dir, script)],
        env=dict(os.environ, **params),
        stderr=subprocess.STDOUT,
    )
    print(f"Running '{script}' with '{params}'. Output ignored")


class Log(db.Model):
    __tablename__ = "logs"

    _db_id = db.Column(db.Integer, primary_key=True)
    _db_step_id = db.Column(db.Integer, db.ForeignKey("task_steps._db_id"))
    _db_step = relationship("TaskStep", back_populates="_db_log")
    _db_text = db.Column(db.String)

    @property
    def step(self) -> "TaskStep":
        return eval(self._db_step)

    @property
    def text(self) -> str:
        return self._db_text

    def __init__(self, _step: "TaskStep", _text: str):
        self._db_step = _step
        self._db_text = _text

    def update(self, text):
        self._db_text = text
        db.session.commit()

    def save(self):
        db.session.add(self)
        db.session.commit()
        return self


class TaskStep(db.Model):
    __tablename__ = "task_steps"

    _db_id = db.Column(db.Integer, primary_key=True)
    _db_type = db.Column(db.String)
    _db_task_id = db.Column(db.Integer, db.ForeignKey("tasks._db_id"))
    _db_task: "Task" = relationship(
        "Task", foreign_keys=[_db_task_id], back_populates="_db_steps"
    )
    _db_log: Log = relationship("Log", back_populates="_db_step", uselist=False)
    done: bool = db.Column(db.Boolean)
    active: bool = db.Column(db.Boolean)
    _db_aborted: bool = db.Column(db.Boolean)
    _db_run_as_root: bool = db.Column(db.Boolean)

    @property
    def logs(self) -> str:
        """If available, gets logs. Otherwise an empty string"""
        if self._db_log is None:
            return ""
        else:
            return self._db_log.text

    @property
    def results(self) -> str:
        return ""

    @property
    def aborted(self) -> bool:
        return self._db_aborted

    @property
    def run_as_root(self) -> bool:
        return self._db_run_as_root

    __mapper_args__ = {"polymorphic_on": _db_type}

    def __init__(self, task: "Task"):
        self._db_task = task
        self.done = False
        self.active = False
        self._db_run_as_root = True

    def next_step(self):
        found_current = False
        for i, step in enumerate(self._db_task._db_steps):
            if found_current and not step.aborted and not step.done:
                return step
            if step is self:
                found_current = True
        return None

    def add_to_db(self):
        db.session.add(self)
        db.session.commit()
        return self

    def can_be_aborted(self) -> bool:
        """Whether this step can be aborted."""
        raise NotImplementedError("Must be implemented by child class")

    def while_active(self):
        """Code to run during the execution."""
        return

    def is_instance_loss_valid_end(self):
        raise NotImplementedError("Must be implemented by child class")

    def status_check(self):
        """Code to ensure step is in valid state."""
        print("Status check", self._db_task.instance)
        if self._db_task.instance is None:
            if self.is_instance_loss_valid_end():
                self._db_task.step_succeeded(check_status=False)
            else:
                self._db_task.step_failed(check_status=False)

    def execute(self):
        """Code to execute."""
        self.active = True
        db.session.commit()

    def description(self):
        """Used for UI."""
        raise NotImplementedError("Must be implemented by child class")

    def note(self):
        return ""

    def abort(self):
        self._db_aborted = True
        self.active = False
        self.done = True
        db.session.commit()

    def _update_log(self, filename):
        if self._db_task.instance is None:
            return
        text = self._db_task.instance.get_logs(filename)
        if self._db_log is None:
            self._db_log = Log(self, text).save()
        else:
            if text.startswith("ssh: connect to host"):
                text = self._db_log.text + "\n" + text
            if text == "Error loading logs, connection timed out.":
                if self._db_log.text.endswith("Error loading logs, connection timed out."):
                    pass
                else:
                    text = self._db_log.text + "\n" + text
            self._db_log.update(text)


class TaskFailure(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_failure"}

    def execute(self):
        super().execute()
        if self._db_task.instance is not None:
            self._db_task.instance.terminate()

    def can_be_aborted(self) -> bool:
        return False

    def is_instance_loss_valid_end(self):
        return True

    def description(self):
        return "Task failed. Shutting down"


class TaskAbortion(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_abortion"}

    def execute(self):
        super().execute()
        if self._db_task.instance is not None:
            self._db_task.instance.terminate()

    def can_be_aborted(self) -> bool:
        return False

    def is_instance_loss_valid_end(self):
        return True

    def description(self):
        return "Task aborted. Shutting down"


class TaskTimeout(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_timeout"}

    def execute(self):
        super().execute()
        self._db_task.instance.terminate()

    def can_be_aborted(self) -> bool:
        return False

    def is_instance_loss_valid_end(self):
        return True

    def description(self):
        return "Task timeout. Shutting down"


class TaskShutdown(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_shutdown"}

    def execute(self):
        super().execute()
        self._db_task.instance.terminate()

    def can_be_aborted(self) -> bool:
        return False

    def is_instance_loss_valid_end(self):
        return True

    def description(self):
        return "Shutting down instance"


class BenchmarkCreate(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_benchmark_create"}

    def _create(self):
        from vnncomp.utils.aws_instance import AwsManager

        success = AwsManager.start_new_toolkit_instance(
            self._db_task.aws_instance_type, self._db_task.ami
        )
        if success:
            db.session.commit()
            self._db_task.step_succeeded()

    def execute(self):
        super().execute()

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def while_active(self):
        super().while_active()
        self._create()

    def description(self):
        return "Instance creation"

    def status_check(self):
        return

    def note(self):
        if self.done:
            return ""
        return f"Queue position { self.queue_position() }. If your position doesn't advance within an hour, please let us know."

    def queue_position(self):
        from vnncomp.utils.task import BenchmarkTask

        return (
            BenchmarkCreate.query.filter(
                (BenchmarkCreate._db_id < self._db_id)
                & (
                    BenchmarkCreate._db_task.has(
                        BenchmarkTask._db_aws_instance_type
                        == self._db_task.aws_instance_type.value
                    )
                )
                & (TaskStep._db_type == "task_benchmark_create")
                & (TaskStep.done == False)
            ).count()
            + 1
        )

    def description(self):
        return "Instance creation"

    def status_check(self):
        return


class BenchmarkInitialize(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_benchmark_initialize"}

    def execute(self):
        super().execute()
        _ping(
            "benchmark",
            "initialize_instance.sh",
            {
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("initialize_instance.log")

    def description(self):
        return "Initialization"


class BenchmarkClone(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_benchmark_clone"}

    def execute(self):
        super().execute()
        _ping(
            "benchmark",
            "clone.sh",
            {
                "repository": self._db_task.repository,
                "hash": self._db_task.hash,
                "script_dir": self._db_task.script_dir,
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("clone.log")

    def description(self):
        return "Cloning"


class BenchmarkRun(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_benchmark_run"}

    def execute(self):
        super().execute()
        _ping(
            "benchmark",
            "run.sh",
            {
                "script_dir": self._db_task.script_dir,
                "vnnlib_dir": self._db_task.vnnlib_dir,
                "onnx_dir": self._db_task.onnx_dir,
                "csv_file": self._db_task.csv_file,
                "csv_onnx_base": self._db_task.csv_onnx_base,
                "csv_vnnlib_base": self._db_task.csv_vnnlib_base,
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("run.log")

    def description(self):
        return "Testing"


class BenchmarkGithubExport(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_benchmark_github_export"}

    def execute(self):
        super().execute()
        _ping(
            "benchmark",
            "github_export.sh",
            {
                "repository": self._db_task.repository,
                "hash": self._db_task.hash,
                "name": self._db_task.sanitized_name,
                "seed": "676744409",
                "script_dir": self._db_task.script_dir,
                "vnnlib_dir": self._db_task.vnnlib_dir,
                "onnx_dir": self._db_task.onnx_dir,
                "csv_file": self._db_task.csv_file,
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
                "sciebo_username": os.environ["SCIEBO_USERNAME"],
                "sciebo_password": os.environ["SCIEBO_PASSWORD"],
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("github_export.log")

    def description(self):
        return "Exporting to GitHub"


class ToolkitCreate(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_create"}

    def __init__(self, task: "Task"):
        super().__init__(task)

    def _create(self):
        from vnncomp.utils.aws_instance import AwsManager

        success = AwsManager.start_new_toolkit_instance(
            self._db_task.aws_instance_type, self._db_task.ami
        )
        if success:
            db.session.commit()
            self._db_task.step_succeeded()

    def execute(self):
        super().execute()

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def while_active(self):
        super().while_active()
        self._create()

    def description(self):
        return "Instance creation"

    def status_check(self):
        return

    def note(self):
        if self.done:
            return ""
        return f"Queue position { self.queue_position() }. If your position doesn't advance within an hour, please let us know."

    def queue_position(self):
        from vnncomp.utils.task import ToolkitTask

        return (
            ToolkitCreate.query.filter(
                (ToolkitCreate._db_id < self._db_id)
                & (
                    ToolkitCreate._db_task.has(
                        ToolkitTask._db_aws_instance_type
                        == self._db_task.aws_instance_type.value
                    )
                )
                & (TaskStep._db_type == "task_toolkit_create")
                & (TaskStep.done == False)
            ).count()
            + 1
        )


class TaskAssign(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_assign"}

    def _assign(self):
        from vnncomp.utils.aws_instance import AwsInstance

        free_instance: Optional[AwsInstance] = AwsInstance.get_next_available(
            self._db_task.aws_instance_type, self._db_task.ami
        )

        if free_instance is not None:
            self._db_task.assign(free_instance)
            print("Connected")

    def execute(self):
        super().execute()
        self._assign()

    def can_be_aborted(self) -> bool:
        return False

    def is_instance_loss_valid_end(self):
        return False

    def while_active(self):
        super().while_active()
        self._assign()

    def description(self):
        return "Assigning AWS instance to this task"

    def status_check(self):
        return


class TaskPause(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_pause"}

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def description(self):
        return "Pause"

    def note(self):
        if self.active:
            return f"Click <a href='{self._success_link()}'>here</a> to proceed."
        return ""

    def _success_link(self):
        return url_for("update_success", id=self._db_task.id)


class ToolkitInitialize(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_initialize"}

    def execute(self):
        super().execute()
        _ping(
            "toolkit",
            "initialize_instance.sh",
            {
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("initialize_instance.log")

    def description(self):
        return "Initialization"


class ToolkitClone(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_clone"}

    def execute(self):
        from vnncomp.utils.task import ToolkitTask

        assert type(self._db_task) is ToolkitTask
        super().execute()
        _ping(
            "toolkit",
            "clone.sh",
            {
                "repository": self._db_task.repository,
                "hash": self._db_task.hash,
                "script_dir": self._db_task.script_dir,
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("clone.log")

    def description(self):
        return "Cloning"


class ToolkitInstall(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_install"}

    def __init__(self, task: "Task", run_as_root: bool):
        super().__init__(task)
        self._db_run_as_root = run_as_root

    def execute(self):
        super().execute()
        _ping(
            "toolkit",
            "install.sh",
            {
                "script_dir": self._db_task.script_dir,
                "sudo": "sudo" if self.run_as_root else "",
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("install.log")

    def description(self):
        return f"Installation (as { 'root' if self.run_as_root else 'non-root' })"


class ToolkitPostInstall(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_post_install"}

    def __init__(self, task: "Task", run_as_root: bool):
        super().__init__(task)
        self._db_run_as_root = run_as_root

    def execute(self):
        from vnncomp.utils.task import ToolkitTask

        assert type(self._db_task) is ToolkitTask
        super().execute()
        _ping(
            "toolkit",
            "post_install.sh",
            {
                "script_dir": self._db_task.script_dir,
                "post_install_tool": self._db_task.post_install_tool,
                "sudo": "sudo" if self.run_as_root else "",
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log("post_install.log")

    def description(self):
        return f"Post-Installation (as { 'root' if self.run_as_root else 'non-root' })"

    def note(self):
        if self.active or self.done:
            return ""
        return f"Click <a href='{self._edit_url()}'>here</a> to edit."

    def _edit_url(self):
        return url_for("toolkit_edit_post_install", id=self._db_task.id)


class ToolkitRun(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_run"}

    benchmark_name = db.Column(db.String)
    run_networks = db.Column(db.String)
    _db_results = db.Column(db.String)

    @property
    def results(self) -> str:
        if self._db_results is None:
            return ""
        else:
            return self._db_results

    def __init__(
        self, task: "Task", benchmark_name: str, run_networks: str, run_as_root: bool
    ):
        super().__init__(task)
        self.benchmark_name = benchmark_name
        self.run_networks = run_networks
        self._db_run_as_root = run_as_root

    def execute(self):
        super().execute()
        _ping(
            "toolkit",
            "run.sh",
            {
                "script_dir": self._db_task.script_dir,
                "benchmark_year": self.benchmark_name[:4],
                "benchmark_name": self.benchmark_name[5:],
                "run_networks": self.run_networks,
                "sudo": "sudo" if self.run_as_root else "",
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        print(self, self._db_task)
        super().status_check()
        self._update_log(f"run_{self.benchmark_name}.log")
        self._db_results = self._db_task.instance.get_logs(
            f"results_{self.benchmark_name}.csv"
        )
        db.session.commit()

    def description(self):
        return f"Execution ({self.benchmark_name} as { 'root' if self.run_as_root else 'non-root' })"


class ToolkitGithubExport(TaskStep):
    __mapper_args__ = {"polymorphic_identity": "task_toolkit_github_export"}

    benchmark_name2 = db.Column(db.String)

    def __init__(self, task: "Task", benchmark_name: str):
        super().__init__(task)
        self.benchmark_name2 = benchmark_name

    def _get_sanitized_benchmark_name(self):
        return "".join(c.lower() if c.isalnum() else "_" for c in self.benchmark_name2)

    def execute(self):
        super().execute()
        _ping(
            "toolkit",
            "github_export.sh",
            {
                "tool_name": self._db_task.sanitized_name,
                "benchmark_name": self._get_sanitized_benchmark_name(),
                "benchmark_id": str(self._db_task.id),
                "benchmark_ip": self._db_task.instance.ip,
            },
        )

    def can_be_aborted(self) -> bool:
        return True

    def is_instance_loss_valid_end(self):
        return False

    def status_check(self):
        super().status_check()
        self._update_log(f"github_export_{self._get_sanitized_benchmark_name()}.log")

    def description(self):
        return f"Exporting to GitHub ({self.benchmark_name2})"
