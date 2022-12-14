from argparse import ArgumentError
from crypt import methods
import time
from typing import Dict, List, Optional

from flask import flash, render_template, redirect, url_for
from flask_login import current_user

from app.main import app
from app.auth import login_required
from app.utils.aws_instance import AwsInstanceType, AwsManager, AwsInstance
from app.utils.task import BenchmarkTask, Task, ToolkitTask
from app.utils.forms import (
    ToolkitEditPostInstallForm,
    ToolkitSubmissionForm,
    BenchmarkSubmissionForm,
)
from app.utils.task_steps import ToolkitRun

MAX_RUNNING_TASKS = 3


def fetch_updates():
    global LAST_UPDATE

    AwsManager.update_instance_list()
    LAST_UPDATE = time.strftime("%A, %d. %B %Y %I:%M:%S %p")


def process_tasks():
    for task in Task.get_in_progress():
        print("Processing task", task)
        task.current_step.status_check()

    for task in Task.get_in_progress():
        task.current_step.while_active()


def scheduler_function():
    fetch_updates()
    process_tasks()


@app.context_processor
def inject_current_user():
    return dict(current_user=current_user)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/toolkit", methods=["GET"])
@login_required
def toolkit_redirect():
    return redirect("/toolkit/details")


@app.route("/toolkit/form", methods=["GET"])
@login_required
def toolkit():
    form = ToolkitSubmissionForm()
    return render_template(
        "toolkit/submission.html",
        form=form,
    )


@app.route("/toolkit/submit", methods=["POST"])
@login_required
def submit():
    form = ToolkitSubmissionForm()
    if not form.validate_on_submit():
        message = "Error processing formular input."
        return render_template("toolkit/submission.html", form=form, message=message)
    if not current_user.admin:
        message = "Submission is closed."
        return render_template("toolkit/submission.html", form=form, message=message)

    aws_instance_type: AwsInstanceType = AwsInstanceType(
        int(form.aws_instance_type.data)
    )
    task = ToolkitTask.save_new(
        _aws_instance_type=aws_instance_type,
        _ami=form.ami.data,
        _name=form.name.data,
        _repository=form.repository.data,
        _hash=form.hash.data,
        _script_dir=form.scripts_dir.data,
        _pause=form.pause.data,
        _post_install_tool=form.post_install_tool.data,
        _benchmarks=form.benchmarks.data,
        _run_networks=form.run_networks.data,
        _run_install_as_root=form.run_install_as_root.data,
        _run_post_install_as_root=form.run_post_install_as_root.data,
        _run_tool_as_root=form.run_tool_as_root.data,
    )

    return redirect(url_for("toolkit_details", id=task.id))


@app.route("/toolkit/resubmit/<id>", methods=["GET"])
@login_required
def toolkit_resubmit(id):
    task: ToolkitTask = ToolkitTask.get(int(id))
    if task is None:
        return render_template("404.html")
    assert type(task) is ToolkitTask
    form = ToolkitSubmissionForm()
    form.aws_instance_type.data = str(task.aws_instance_type.value)
    form.ami.data = task.ami
    form.name.data = task.name
    form.repository.data = task.repository
    form.hash.data = task.hash
    form.scripts_dir.data = task.script_dir
    form.pause.data = task.pause
    form.post_install_tool.data = task.post_install_tool
    form.benchmarks.data = task.benchmarks
    form.run_networks.data = task.run_networks
    form.run_install_as_root.data = task.run_install_as_root
    form.run_post_install_as_root.data = task.run_post_install_as_root
    form.run_tool_as_root.data = task.run_tool_as_root

    return render_template("toolkit/submission.html", form=form)


@app.route("/toolkit/details", methods=["GET"])
@login_required
def toolkit_list():
    tasks = ToolkitTask.get_all_uservisible()
    return render_template("toolkit/list.html", tasks=tasks)


@app.route("/toolkit/details/<id>", methods=["GET"])
@login_required
def toolkit_details(id):
    task = ToolkitTask.get(int(id))
    if task is None:
        return render_template("404.html")
    return render_template("toolkit/details.html", task=task)


@app.route("/toolkit/edit_post_install/<id>", methods=["GET", "POST"])
@login_required
def toolkit_edit_post_install(id):
    task = ToolkitTask.get(int(id))
    if task is None or not task.can_edit_post_install:
        return render_template("404.html")
    form = ToolkitEditPostInstallForm()
    message = ""
    if form.validate_on_submit():
        if not task.can_edit_post_install:
            message = "The post-install script cannot be edited anymore."
        else:
            task.set_post_install_script(form.post_install_tool.data)
            message = "Script successfully updated."
    else:
        form.post_install_tool.data = task.post_install_tool
    return render_template(
        "toolkit/edit_post_install.html", form=form, message=message, id=id
    )


@app.route("/toolkit/abort/<id>", methods=["GET"])
@login_required
def toolkit_abort(id):
    task = ToolkitTask.get(int(id))
    assert task.current_step.can_be_aborted() and not task.done
    task.abort()
    return redirect(url_for("toolkit_details", id=id))


@app.route("/benchmark/form", methods=["GET"])
def benchmark():
    form = BenchmarkSubmissionForm()
    return render_template("benchmark/submission.html", form=form)


@app.route("/benchmark/pip", methods=["GET"])
def benchmark_pip():
    return render_template("benchmark/pip.html")


@app.route("/benchmark/submit", methods=["POST"])
def benchmark_submit():
    form = BenchmarkSubmissionForm()
    if not form.validate_on_submit():
        message = "Error processing formular input."
        return render_template("benchmark/submission.html", form=form, message=message)

    task = BenchmarkTask.save_new(
        _aws_instance_type=AwsInstanceType.T2LARGE,
        _name=form.name.data,
        _repository=form.repository.data,
        _hash=form.hash.data,
        _script_dir=form.scripts_dir.data,
        _vnnlib_dir=form.vnnlib_dir.data,
        _onnx_dir=form.onnx_dir.data,
        _csv_file=form.csv_file.data,
        _csv_onnx_base=form.csv_onnx_base.data,
        _csv_vnnlib_base=form.csv_vnnlib_base.data,
    )

    return redirect(url_for("benchmark_details", id=task.id))


@app.route("/benchmark/details", methods=["GET"])
def benchmark_list():
    tasks = BenchmarkTask.get_all()
    return render_template("benchmark/list.html", tasks=tasks)


@app.route("/benchmark/details/<id>", methods=["GET"])
def benchmark_details(id):
    task = BenchmarkTask.get(int(id))
    return render_template("benchmark/details.html", task=task)


@app.route("/benchmark/resubmit/<id>", methods=["GET"])
def benchmark_resubmit(id):
    task: BenchmarkTask = BenchmarkTask.get(int(id))
    form = BenchmarkSubmissionForm()
    form.name.data = task.name
    form.repository.data = task.repository
    form.hash.data = task.hash
    form.scripts_dir.data = task.script_dir
    form.vnnlib_dir.data = task.vnnlib_dir
    form.onnx_dir.data = task.onnx_dir
    form.csv_file.data = task.csv_file
    form.csv_onnx_base.data = task.csv_onnx_base
    form.csv_vnnlib_base.data = task.csv_vnnlib_base

    return render_template("benchmark/submission.html", form=form)


@app.route("/benchmark/abort/<id>", methods=["GET"])
def benchmark_abort(id):
    task = BenchmarkTask.get(int(id))
    assert task.current_step.can_be_aborted() and not task.done
    task.abort()
    return redirect(url_for("benchmark_details", id=id))


@app.route("/update/<id>/success")
def update_success(id):
    task: Task = Task.get(id)
    task.step_succeeded()
    if current_user.is_authenticated:
        return redirect(url_for("toolkit_details", id=id))
    return "OK"


@app.route("/update/<id>/failure")
def update_failure(id):
    task: Task = Task.get(id)
    task.step_failed()
    return "OK"


@app.route("/manual_update")
def manual_update():
    fetch_updates()
    process_tasks()
    return "/"


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500
