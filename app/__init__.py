from typing import Dict, List, Optional
import time
import atexit
import os

from flask import Flask
from flask_bootstrap import Bootstrap
from sqlalchemy import MetaData
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy


from apscheduler.schedulers.background import BackgroundScheduler

convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

metadata = MetaData(naming_convention=convention)
db = SQLAlchemy(metadata=metadata)
migrate = Migrate()
login_manager = LoginManager()

# Flask-Bootstrap requires this line


def create_app():
    app = Flask(__name__)

    # Flask-WTF requires an enryption key - the string can be anything
    app.config["SECRET_KEY"] = os.getenv('SECRET_KEY', 'some secret key')
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////var/www/html/vnncomp/vnncomp.db"

    from app.utils.task import Task, BenchmarkTask, ToolkitTask
    from app.utils.task_steps import (
        TaskStep,
        TaskAssign,
        TaskShutdown,
        TaskAbortion,
        TaskFailure,
        TaskTimeout,
        BenchmarkCreate,
        BenchmarkInitialize,
        BenchmarkClone,
        BenchmarkRun,
        BenchmarkGithubExport,
    )
    from app.utils.aws_instance import AwsInstance, AwsManager
    from app.utils.user import User

    Bootstrap(app)

    db.init_app(app)
    migrate.init_app(app, db, render_as_batch=True)
    login_manager.init_app(app)

    return app
