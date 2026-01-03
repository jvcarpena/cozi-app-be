from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    Inherit from this class to automatically include SQLAlchemy's
    declarative features for ORM mapping.
    """

    pass


class AuditMixin:
    """
    Mixin to add automatic auditing fields to a SQLAlchemy model.
    """

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=func.now())

    updated_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime, onupdate=func.now())

    deleted_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
