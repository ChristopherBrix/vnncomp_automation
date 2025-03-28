from typing import Dict, List, Optional
import os
import re
import time
from argparse import ArgumentError
from crypt import methods
import requests
import yaml

from flask import flash, render_template, redirect, request, url_for, abort, jsonify
from flask_login import current_user

from vnncomp.main import app
from vnncomp.auth import admin_permissions_required, login_required
from vnncomp.utils.aws_instance import AwsInstanceType, AwsManager, AwsInstance
from vnncomp.utils.settings import Settings
from vnncomp.utils.task import BenchmarkTask, Task, ToolkitTask
from vnncomp.utils.user import User
from vnncomp.utils.forms import (
    ToolkitEditPostInstallForm,
    ToolkitSubmissionForm,
    BenchmarkSubmissionForm, LoginForm,
    ToolkitSubmissionFormAdmin,
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
    ToolkitRestart,
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
        print("Status check for task", task)
        task.current_step.status_check()

    for task in Task.get_in_progress():
        print("Processing task", task)
        task.current_step.while_active()


def scheduler_function():
    fetch_updates()
    process_tasks()


@app.context_processor
def inject_current_user():
    return dict(current_user=current_user)

@app.context_processor
def inject_settings():
    return dict(Settings=Settings)

@app.context_processor
def inject_env():
    return dict(env=os.environ)


@app.route("/")
def index():
    # abort(404)
    if current_user.is_authenticated:
        if True:
            return toolkit_redirect()
        else:
            return benchmark_redirect()

    else:
        form = LoginForm()
        return render_template("index.html",
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
    if current_user.admin:
        form = ToolkitSubmissionFormAdmin()
    else:
        form = ToolkitSubmissionForm()
    form.eni.data = current_user.eni
    return render_template(
        "toolkit/submission.html",
        form=form,
    )


@app.route("/toolkit/submit", methods=["POST"])
@login_required
def submit():
    if current_user.admin:
        form: ToolkitSubmissionFormAdmin = ToolkitSubmissionFormAdmin()
    else:
        form: ToolkitSubmissionForm = ToolkitSubmissionForm()
    if not form.validate_on_submit():
        message = "Error processing formular input."
        return render_template("toolkit/submission.html", form=form, message=message)
    if not current_user.admin and not Settings.users_can_submit_tools():
        message = "Submission is closed."
        return render_template("toolkit/submission.html", form=form, message=message)

    pattern = re.compile("https://([a-zA-Z0-9_]*@)?github\.com/")
    url: str = form.repository.data
    if not pattern.match(url):
        message = f"Repository URL must have the format https://github.com/ABC/DEF or https://PAT@github.com/ABC/DEF"
        return render_template("toolkit/submission.html", form=form, message=message)

    pwd = None
    if not url.startswith("https://github.com"):
        assert "@" in url
        pwd = url.split("@")[0][len("https://"):]
        url = "https://" + "".join(url.split("@")[1:])

    yaml_config_url = f"{url.replace('github.com', 'raw.githubusercontent.com')}/{form.hash.data}/{form.yaml_config_file.data}"
    config_request = requests.get(yaml_config_url, auth=(None, pwd))
    if config_request.status_code != 200:
        message = f"Config ({yaml_config_url}) could not be loaded, error code {config_request.status_code}"
        return render_template("toolkit/submission.html", form=form, message=message)
    
    parsed_config = yaml.safe_load(config_request.content)
    for k in [
        "name",
        "ami",
        "scripts_dir",
        "manual_installation_step",
        "run_installation_script_as_root",
        "run_post_installation_script_as_root",
        "run_toolkit_as_root",
        "description",
    ]:
        if k not in parsed_config:
            message = f"Config file ({yaml_config_url}) has no value for mandatory attribute {k}"
            return render_template("toolkit/submission.html", form=form, message=message)
    for k in [
        "manual_installation_step",
        "run_installation_script_as_root",
        "run_post_installation_script_as_root",
        "run_toolkit_as_root",
    ]:
        if not isinstance(parsed_config[k], bool):
            message = f"Config file value for {k} must be boolean"
            return render_template("toolkit/submission.html", form=form, message=message)
    
    if parsed_config["ami"] not in [
        "ami-0280f3286512b1b99",
        "ami-0892d3c7ee96c0bf7",
        "ami-0d70546e43a941d70",
        "ami-0cce14f90c7ec05b5",
        "ami-05865edb0dba554ff",
        "ami-0aff18ec83b712f05",
        "ami-04fbaf1323e01bd2b",
    ]:
        message = f"AMI image {parsed_config['ami']} invalid"
        return render_template("toolkit/submission.html", form=form, message=message)

    aws_instance_type: AwsInstanceType = AwsInstanceType(
        int(form.aws_instance_type.data)
    )
    selected_benchmarks = form.benchmarks.data
    pause = parsed_config["manual_installation_step"]
    if current_user.admin:
        assert type(form) is ToolkitSubmissionFormAdmin
        if form.reverse_order.data:
            selected_benchmarks.reverse()
        benchmarks_per_submission = form.split.data
        if benchmarks_per_submission == 0:
            benchmarks_per_submission = len(selected_benchmarks)
        export_results = form.export_results.data
        if form.force_pause.data and form.force_no_pause.data:
            message = "You cannot both force a pause and force not to pause"
            return render_template("toolkit/submission.html", form=form, message=message)
        if not pause and form.force_pause.data:
            pause = True
        if pause and form.force_no_pause.data:
            pause = False
        if form.save_with_user_id.data is not None:
            user_overwrite = User.query.get(form.save_with_user_id.data)
            if user_overwrite is None:
                message = "User ID not found"
                return render_template("toolkit/submission.html", form=form, message=message)
        else:
            user_overwrite = None
    else:
        assert type(form) is ToolkitSubmissionForm
        benchmarks_per_submission = len(selected_benchmarks)
        export_results = False
        user_overwrite = None
    if form.eni.data == "":
        eni = None
    else:
        eni = form.eni.data
    for i in range(0, len(selected_benchmarks), benchmarks_per_submission):
        task = ToolkitTask.save_new(
            _aws_instance_type=aws_instance_type,
            _eni=eni,
            _ami=parsed_config["ami"],
            _name=parsed_config["name"],
            _repository=form.repository.data,
            _hash=form.hash.data,
            _yaml_config_file=form.yaml_config_file.data,
            _yaml_config_content=config_request.content.decode("utf-8"),
            _script_dir=parsed_config["scripts_dir"],
            _pause=pause,
            _post_install_tool=form.post_install_tool.data,
            _benchmarks=selected_benchmarks[i:i+benchmarks_per_submission],
            _run_networks=form.run_networks.data,
            _run_install_as_root=parsed_config["run_installation_script_as_root"],
            _run_post_install_as_root=parsed_config["run_post_installation_script_as_root"],
            _run_tool_as_root=parsed_config["run_toolkit_as_root"],
            _export_results=export_results,
            _pause_after_postinstallation=form.pause_after_postinstallation.data,
            _restart_after_postinstallation=form.restart_after_postinstallation.data,
            _user_overwrite=user_overwrite,
        )

    return redirect(url_for("toolkit_details", id=task.id))


@app.route("/toolkit/resubmit/<id>", methods=["GET"])
@login_required
def toolkit_resubmit(id):
    task: ToolkitTask = ToolkitTask.get(int(id))
    if task is None:
        return render_template("404.html")
    assert type(task) is ToolkitTask
    if current_user.admin:
        form: ToolkitSubmissionFormAdmin = ToolkitSubmissionFormAdmin()
    else:
        form = ToolkitSubmissionForm()
    form.aws_instance_type.data = str(task.aws_instance_type.value)
    form.eni.data = task.eni
    form.repository.data = task.repository
    form.hash.data = task.hash
    form.yaml_config_file.data = task.yaml_config_file
    form.run_networks.data = task.run_networks
    form.post_install_tool.data = task.post_install_tool
    form.benchmarks.data = task.benchmarks
    form.pause_after_postinstallation.data = task.pause_after_postinstallation
    form.restart_after_postinstallation.data = task.restart_after_postinstallation

    return render_template("toolkit/submission.html", form=form)


@app.route("/toolkit/details", methods=["GET"])
@login_required
def toolkit_list():
    tasks = ToolkitTask.get_all_uservisible()
    tasks.reverse()
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
    if task is None:
        return render_template("404.html")
    assert task.current_step.can_be_aborted() and not task.done
    task.abort()
    return redirect(url_for("toolkit_details", id=id))


@app.route("/toolkit/sanitize_abort/<id>", methods=["GET"])
@login_required
@admin_permissions_required
def toolkit_sanitize_abort(id):
    task = ToolkitTask.get(int(id))
    if task is None:
        return render_template("404.html")
    if task.current_step is not None:
        return f"The current step is {task.current_step}, no sanitization necessary"
    task.sanitize_abort()
    return redirect(url_for("toolkit_details", id=id))


@app.route("/toolkit/change_owner/<task_id>", methods=["GET"])
@login_required
@admin_permissions_required
def change_owner(task_id: str):
    task: Task = Task.get(int(task_id))
    if task is None:
        return render_template("404.html")
    users = User.query.all()
    return render_template("toolkit/change_owner.html", task=task, users=users)


@app.route("/toolkit/change_owner/<task_id>/<new_owner_id>", methods=["GET"])
@login_required
@admin_permissions_required
def change_owner_submit(task_id: str, new_owner_id: str):
    task: Task = Task.get(int(task_id))
    if task is None:
        return render_template("404.html")
    user = User.query.get(int(new_owner_id))
    if user is None:
        return "User not found"
    task.set_owner(user)
    return redirect(url_for("toolkit_list"))


@app.route("/benchmark/form", methods=["GET"])
@login_required
def benchmark():
    form = BenchmarkSubmissionForm()
    return render_template("benchmark/submission.html", form=form)


@app.route("/benchmark/pip", methods=["GET"])
@login_required
def benchmark_pip():
    return render_template("benchmark/pip.html")


@app.route("/benchmark/submit", methods=["POST"])
@login_required
def benchmark_submit():
    form = BenchmarkSubmissionForm()
    if not form.validate_on_submit():
        message = "Error processing formular input."
        return render_template("benchmark/submission.html", form=form, message=message)
    if not current_user.admin and not Settings.users_can_submit_benchmarks():
        message = "Submission is closed."
        return render_template("benchmark/submission.html", form=form, message=message)

    task = BenchmarkTask.save_new(
        _aws_instance_type=AwsInstanceType.T2MICRO,
        _name=form.name.data,
        _repository=form.repository.data,
        _hash=form.hash.data,
        _script_dir=".",
        _vnnlib_dir="vnnlib",
        _onnx_dir="onnx",
        _csv_file="instances.csv",
        _csv_onnx_base="",
        _csv_vnnlib_base="",
    )

    return redirect(url_for("benchmark_details", id=task.id))


@app.route("/benchmark/details", methods=["GET"])
@login_required
def benchmark_list():
    tasks = BenchmarkTask.get_all()
    return render_template("benchmark/list.html", tasks=tasks)


@app.route("/benchmark/details/<id>", methods=["GET"])
@login_required
def benchmark_details(id: str):
    task = BenchmarkTask.get(int(id))
    if task is None:
        return render_template("404.html")
    task_step_ids = [step._db_id for step in task._db_steps]
    return render_template("benchmark/details.html", task=task, task_step_ids=task_step_ids)

@app.route("/benchmark/details/task/<id>", methods=["GET"])
@login_required
def benchmark_details_task_status(id: str):
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
def benchmark_taskstep_async(id: str):
    taskstep = TaskStep.query.get(int(id))
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
@login_required
def benchmark_resubmit(id: str):
    task: BenchmarkTask = BenchmarkTask.get(int(id))
    if task is None:
        return render_template("404.html")
    form = BenchmarkSubmissionForm()
    form.name.data = task.name
    form.repository.data = task.repository
    form.hash.data = task.hash

    return render_template("benchmark/submission.html", form=form)


@app.route("/benchmark/abort/<id>", methods=["GET"])
@login_required
def benchmark_abort(id: str):
    task = BenchmarkTask.get(int(id))
    if task is None:
        return render_template("404.html")
    assert task.current_step.can_be_aborted() and not task.done
    task.abort()
    return redirect(url_for("benchmark_details", id=id))

@app.route("/update/<id>/success")
def update_success(id: str):
    task: Task = Task.get(int(id))
    if task is None:
        return render_template("404.html")
    task.step_succeeded()
    if current_user.is_authenticated:
        return redirect(url_for("toolkit_details", id=id))
    return "OK"


@app.route("/force_step/<task_id>/<step_id>")
@login_required
@admin_permissions_required
def force_step(task_id: str, step_id: str):
    task: Task = Task.get(int(task_id))
    if task is None:
        return render_template("404.html")
    task.force_step(int(step_id))
    return redirect(url_for("toolkit_details", id=task_id))


@app.route("/update/<id>/failure")
def update_failure(id: str):
    task: Task = Task.get(int(id))
    if task is None:
        return render_template("404.html")
    task.step_failed()
    return "OK"

@app.route("/user/profile")
@login_required
def user_profile():
    return render_template("user/profile.html")

@app.route("/admin")
@login_required
@admin_permissions_required
def admin():
    return render_template("admin/index.html")

@app.route("/admin/users", methods=["GET"])
@login_required
@admin_permissions_required
def admin_users():
    return render_template("admin/users.html", users=User.query.all())

@app.route("/admin/settings")
@login_required
@admin_permissions_required
def admin_settings():
    return render_template("admin/settings.html")

@app.route("/admin/settings/set/<parameter>", methods=["GET"])
@login_required
@admin_permissions_required
def admin_settings_set(parameter: str):
    new_value = request.args.get("new_value")
    if parameter == "aws_enabled":
        Settings.set_aws_enabled(new_value == "1")
    elif parameter == "terminate_at_end":
        Settings.set_terminate_at_end(new_value == "1")
    elif parameter == "terminate_on_failure":
        Settings.set_terminate_on_failure(new_value == "1")
    elif parameter == "allow_non_admin_login":
        Settings.set_allow_non_admin_login(new_value == "1")
    elif parameter == "users_can_submit_benchmarks":
        Settings.set_users_can_submit_benchmarks(new_value == "1")
    elif parameter == "users_can_submit_tools":
        Settings.set_users_can_submit_tools(new_value == "1")
    elif parameter == "instance_timeout":
        try:
            Settings.set_instance_timeout(int(new_value))
        except ValueError:
            return "Invalid parameter"
    else:
        return "Invalid parameter"
    return redirect("/admin/settings")

@app.route("/admin/users/<id>/assign_eni", methods=["GET"])
@login_required
@admin_permissions_required
def admin_user_assign_eni(id: str):
    user = User.query.get(int(id))
    if user is None:
        return render_template("404.html")
    AwsManager.assign_new_eni(user)
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<id>/delete_eni", methods=["GET"])
@login_required
@admin_permissions_required
def admin_user_delete_eni(id: str):
    user = User.query.get(int(id))
    if user is None:
        return render_template("404.html")
    AwsManager.delete_eni(user)
    return redirect(url_for("admin_users"))

@app.route("/admin/users/<id>/login", methods=["GET"])
@login_required
@admin_permissions_required
def admin_user_login(id: str):
    user = User.query.get(int(id))
    if user is None:
        return render_template("404.html")
    logout_user()
    login_user(user)
    return redirect(url_for("index"))

@app.route("/manual_update")
def manual_update():
    if Settings.aws_enabled():
        fetch_updates()
        process_tasks()
    else:
        return "Connection to AWS not enabled"
    return "ok"

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()
@scheduler.task('interval', id='automatic_update', seconds=60*5, misfire_grace_time=10)
def automatic_update():
    with scheduler.app.app_context():
        manual_update()


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def internal_server_error(e):
    return render_template("500.html"), 500
