from typing import Optional

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import BYTEA
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base


class User(Base, AuditMixin):
    __tablename__ = "users"

    __mapper_args__ = {
        "polymorphic_on": "user_type",
    }

    id: Mapped[str] = mapped_column(String(256), primary_key=True)

    email_address: Mapped[Optional[str]] = mapped_column(String(256))

    user_type: Mapped[str] = mapped_column(String(256))

    hashed_password: Mapped[Optional[bytes]] = mapped_column(BYTEA)
