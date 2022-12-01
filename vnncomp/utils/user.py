"""Database models."""
from typing import TYPE_CHECKING, List
import sqlalchemy
from vnncomp import db
from flask_login import UserMixin
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

if TYPE_CHECKING:
    from vnncomp.utils.task import ToolkitTask


class User(UserMixin, db.Model):
    """User account model."""

    __tablename__ = "flasklogin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(40), unique=True, nullable=False)
    password = db.Column(
        db.String(200), primary_key=False, unique=False, nullable=False
    )
    created_on = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    last_login = db.Column(db.DateTime, index=False, unique=False, nullable=True)
    enabled = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sqlalchemy.sql.expression.literal(False),
    )
    admin = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        server_default=sqlalchemy.sql.expression.literal(False),
    )
    submitted_toolkits: List["ToolkitTask"] = relationship(
        "ToolkitTask", back_populates="_db_user"
    )

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password, method="sha256")

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)

    def enable(self):
        self.enabled = True
        db.session.commit()

    def disable(self):
        assert not self.admin, "Cannot disable an admin account"

        self.enabled = False
        db.session.commit()

    @property
    def total_used_runtime(self) -> int:
        return sum(
            t._db_total_runtime if t._db_total_runtime is not None else 0
            for t in self.submitted_toolkits
        )

    def __repr__(self):
        return "<User {}>".format(self.username)
