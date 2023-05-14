from argparse import ArgumentError
from crypt import methods
import time
from typing import Dict, List, Optional

from flask import flash, render_template, redirect, url_for, abort, jsonify
from flask_login import current_user

from vnncomp.main import app
from vnncomp.auth import login_required
from vnncomp.utils.aws_instance import AwsInstanceType, AwsManager, AwsInstance
from vnncomp.utils.task import BenchmarkTask, Task, ToolkitTask
from vnncomp.utils.forms import (
    ToolkitEditPostInstallForm,
    ToolkitSubmissionForm,
    BenchmarkSubmissionForm, LoginForm,
)
from vnncomp.utils.task_steps import ToolkitRun

from flask_login import login_required, logout_user, current_user, login_user
from flask_apscheduler import APScheduler

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

MAX_RUNNING_TASKS = 3
print("Website should be online")


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
    # abort(404)
    if current_user.is_authenticated:
        if False:
            return toolkit_redirect()
        else:
            return benchmark_redirect()

    else:
        form = LoginForm()
        return render_template("index___.html",
                               form=form)


@app.route("/toolkit", methods=["GET"])
@login_required
def toolkit_redirect():
    return redirect("/toolkit/details")

@app.route("/benchmark", methods=["GET"])
@login_required
def benchmark_redirect():
    return redirect("/benchmark/details")

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

    task_step_ids = [step._db_id for step in task._db_steps]

    return render_template("toolkit/details.html", task=task, task_step_ids=task_step_ids)


@app.route("/toolkit/details/task/<id>", methods=["GET"])
@login_required
def toolkit_details_task_status(id):
    task = ToolkitTask.get(int(id))
    if task is None:
        return jsonify({"error": "not found"})

    if task.done:
        return jsonify({
            "done": True,
            "output": f"(total runtime {task.total_runtime // (60 * 60)} hours, {task.total_runtime % (60 * 60) // (60)} minutes)"
        })
    else:

        abort_text = ""
        if task.current_step.can_be_aborted():
            abort_text += f"(<a href='{url_for('toolkit_abort', id=task.id)}'>abort</a>)"
        else:
            abort_text += "(cannot be aborted right now)"

        return jsonify({
            "done": False,
            "output": f"(runtime so far {task.total_runtime // (60 * 60)} hours, {task.total_runtime % (60 * 60) // (60)} minutes) {abort_text}"
        })


@app.route("/toolkit/details/step/<id>", methods=["GET"])
@login_required
def toolkit_taskstep_async(id):
    # task = ToolkitTask.get(int(id))
    taskstep = TaskStep.query.get(id)
    if taskstep is None:
        return jsonify({"error": "not found"})

    from datetime import datetime, timezone

    status = ""
    if taskstep.aborted:
        status = "Aborted."
    elif taskstep.done:
        status = "Done."
    elif taskstep.active:
        status = "Running."
    else:
        status = "Pending."

    return jsonify({
        "description": taskstep.description(),
        "logs": taskstep.logs,
        "results": taskstep.results,
        "note": taskstep.note(),
        "status": status,
        "time": datetime.now(timezone.utc)
    })


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
        _aws_instance_type=AwsInstanceType.T2MICRO,
        _name=form.name.data,
        _repository=form.repository.data,
        _hash=form.hash.data,
        _script_dir="",
        _vnnlib_dir="vnnlib",
        _onnx_dir="onnx",
        _csv_file="instances.csv",
        _csv_onnx_base="",
        _csv_vnnlib_base="",
    )

    return redirect(url_for("benchmark_details", id=task.id))


@app.route("/benchmark/details", methods=["GET"])
def benchmark_list():
    tasks = BenchmarkTask.get_all()
    return render_template("benchmark/list.html", tasks=tasks)


@app.route("/benchmark/details/<id>", methods=["GET"])
def benchmark_details(id):
    task = BenchmarkTask.get(int(id))
    task_step_ids = [step._db_id for step in task._db_steps]
    return render_template("benchmark/details.html", task=task, task_step_ids=task_step_ids)

@app.route("/benchmark/details/task/<id>", methods=["GET"])
@login_required
def benchmark_details_task_status(id):
    task = BenchmarkTask.get(int(id))
    if task is None:
        return jsonify({"error": "not found"})

    if task.done:
        return jsonify({
            "done": True,
            "output": f"(total runtime {task.total_runtime // (60 * 60)} hours, {task.total_runtime % (60 * 60) // (60)} minutes)"
        })
    else:

        abort_text = ""
        if task.current_step.can_be_aborted():
            abort_text += f"(<a href='{url_for('benchmark_abort', id=task.id)}'>abort</a>)"
        else:
            abort_text += "(cannot be aborted right now)"

        return jsonify({
            "done": False,
            "output": f"(runtime so far {task.total_runtime // (60 * 60)} hours, {task.total_runtime % (60 * 60) // (60)} minutes) {abort_text}"
        })

@app.route("/benchmark/details/step/<id>", methods=["GET"])
@login_required
def benchmark_taskstep_async(id):
    # task = ToolkitTask.get(int(id))
    taskstep = TaskStep.query.get(id)
    if taskstep is None:
        return jsonify({"error": "not found"})

    from datetime import datetime, timezone

    status = ""
    if taskstep.aborted:
        status = "Aborted."
    elif taskstep.done:
        status = "Done."
    elif taskstep.active:
        status = "Running."
    else:
        status = "Pending."

    return jsonify({
        "description": taskstep.description(),
        "logs": taskstep.logs,
        "results": taskstep.results,
        "note": taskstep.note(),
        "status": status,
        "time": datetime.now(timezone.utc)
    })


@app.route("/benchmark/resubmit/<id>", methods=["GET"])
def benchmark_resubmit(id):
    task: BenchmarkTask = BenchmarkTask.get(int(id))
    form = BenchmarkSubmissionForm()
    form.name.data = task.name
    form.repository.data = task.repository
    form.hash.data = task.hash

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

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
@scheduler.task('interval', id='automatic_update', seconds=60, misfire_grace_time=10)
def automatic_update():
    with scheduler.app.app_context():
        manual_update()


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500
