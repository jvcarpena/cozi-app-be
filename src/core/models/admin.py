from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base


class Admin(Base, AuditMixin):

    __tablename__ = "admins"

    __mapper_args__ = {"polymorphic_identity": "admin"}

    id: Mapped[Any] = mapped_column(ForeignKey("users.id"), primary_key=True)

    organization_id: Mapped[int] = mapped_column()

    resort_id: Mapped[int] = mapped_column()

    profile_picture: Mapped[Optional[str]] = mapped_column(String(256))

    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column()

    active_token: Mapped[Optional[str]] = mapped_column(Text)
