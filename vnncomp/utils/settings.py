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

    def __init__(
        self,
        aws_enabled: bool,
        terminate_on_failure: bool,
        allow_non_admin_login: bool,
    ):
        self._db_aws_enabled = aws_enabled
        self._db_aws_terminate_on_failure = terminate_on_failure
        self._db_allow_non_admin_login = allow_non_admin_login

    @classmethod
    def init(cls):
        assert cls.query.count() <= 1
        settings = cls.query.first()
        if settings is None:
            settings = cls(
                aws_enabled=False,
                terminate_on_failure=True,
                allow_non_admin_login=True,
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
