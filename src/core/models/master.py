from typing import Any, Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base


class Master(Base, AuditMixin):

    __tablename__ = "masters"

    __mapper_args__ = {"polymorphic_identity": "master"}

    id: Mapped[Any] = mapped_column(ForeignKey("users.id"), primary_key=True)

    project_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))

    active_token: Mapped[Optional[str]] = mapped_column(Text)
