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

    @property
    def aws_enabled(self) -> bool:
        return self._db_aws_enabled

    def __init__(
        self,
        aws_enabled: bool,
    ):
        self._db_aws_enabled = aws_enabled

    @classmethod
    def init(cls):
        assert cls.query.count() <= 1
        settings = cls.query.first()
        if settings is None:
            settings = cls(aws_enabled=False)
            db.session.add(settings)
            db.session.commit()

    @classmethod
    def enable_aws(cls):
        settings = Settings.query.first()
        settings._db_aws_enabled = True
        db.session.commit()
    
    @classmethod
    def disable_aws(cls):
        settings = Settings.query.first()
        settings._db_aws_enabled = False
        db.session.commit()
