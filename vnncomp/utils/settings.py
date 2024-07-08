from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
import enum
from functools import total_ordering
from typing import TYPE_CHECKING, Dict, List, Optional

from flask_login import current_user
import sqlalchemy

from vnncomp import db

class Settings(db.Model):
    __tablename__ = "settings"

    _db_id = db.Column(db.Integer, primary_key=True)
    _db_aws_enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sqlalchemy.sql.expression.literal(False),
    )
    _db_aws_terminate_at_end = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=sqlalchemy.sql.expression.literal(True),
    )
    _db_aws_terminate_on_failure = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=sqlalchemy.sql.expression.literal(True),
    )
    _db_allow_non_admin_login = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        server_default=sqlalchemy.sql.expression.literal(True),
    )
    _db_users_can_submit_benchmarks = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sqlalchemy.sql.expression.literal(False),
    )
    _db_users_can_submit_tools = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sqlalchemy.sql.expression.literal(False),
    )
    _db_instance_timeout = db.Column(
        db.Integer,
        nullable=False,
        default=4,
        server_default=sqlalchemy.sql.expression.literal(4),
    )

    def __init__(
        self,
        aws_enabled: bool,
        terminate_at_end: bool,
        terminate_on_failure: bool,
        allow_non_admin_login: bool,
        users_can_submit_benchmarks: bool,
        users_can_submit_tools: bool,
        instance_timeout: int,
    ):
        self._db_aws_enabled = aws_enabled
        self._db_aws_terminate_at_end = terminate_at_end
        self._db_aws_terminate_on_failure = terminate_on_failure
        self._db_allow_non_admin_login = allow_non_admin_login
        self._db_users_can_submit_benchmarks = users_can_submit_benchmarks
        self._db_users_can_submit_tools = users_can_submit_tools
        self._db_instance_timeout = instance_timeout

    @classmethod
    def init(cls):
        assert cls.query.count() <= 1
        settings = cls.query.first()
        if settings is None:
            settings = cls(
                aws_enabled=False,
                terminate_at_end=False,
                terminate_on_failure=True,
                allow_non_admin_login=True,
                users_can_submit_benchmarks=False,
                users_can_submit_tools=False,
                instance_timeout=4,
            )
            db.session.add(settings)
            db.session.commit()

    @classmethod
    def aws_enabled(cls) -> bool:
        return cls.query.first()._db_aws_enabled

    @classmethod
    def set_aws_enabled(cls, aws_enabled: bool):
        settings = cls.query.first()
        settings._db_aws_enabled = aws_enabled
        db.session.commit()

    @classmethod
    def terminate_at_end(cls) -> bool:
        return cls.query.first()._db_aws_terminate_at_end

    @classmethod
    def set_terminate_at_end(cls, terminate_at_end: bool):
        settings = cls.query.first()
        settings._db_aws_terminate_at_end = terminate_at_end
        db.session.commit()

    @classmethod
    def terminate_on_failure(cls) -> bool:
        return cls.query.first()._db_aws_terminate_on_failure
    
    @classmethod
    def set_terminate_on_failure(cls, terminate_on_failure: bool):
        settings = cls.query.first()
        settings._db_aws_terminate_on_failure = terminate_on_failure
        db.session.commit()

    @classmethod
    def allow_non_admin_login(cls) -> bool:
        return cls.query.first()._db_allow_non_admin_login

    @classmethod
    def set_allow_non_admin_login(cls, allow_non_admin_login: bool):
        settings = cls.query.first()
        settings._db_allow_non_admin_login = allow_non_admin_login
        db.session.commit()

    @classmethod
    def users_can_submit_benchmarks(cls) -> bool:
        return cls.query.first()._db_users_can_submit_benchmarks

    @classmethod
    def set_users_can_submit_benchmarks(cls, users_can_submit_benchmarks: bool):
        settings = cls.query.first()
        settings._db_users_can_submit_benchmarks = users_can_submit_benchmarks
        db.session.commit()

    @classmethod
    def users_can_submit_tools(cls) -> bool:
        return cls.query.first()._db_users_can_submit_tools

    @classmethod
    def set_users_can_submit_tools(cls, users_can_submit_tools: bool):
        settings = cls.query.first()
        settings._db_users_can_submit_tools = users_can_submit_tools
        db.session.commit()

    @classmethod
    def instance_timeout(cls) -> int:
        return cls.query.first()._db_instance_timeout

    @classmethod
    def set_instance_timeout(cls, instance_timeout: int):
        settings = cls.query.first()
        settings._db_instance_timeout = instance_timeout
        db.session.commit()