from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import user
from core.models import manager_verification


class Admin(user.User):
    """
    The person a master puts in charge of ONE resort. An admin is never created by signing up, a master invites them.
    """

    __tablename__ = "admins"

    __mapper_args__ = {"polymorphic_identity": "admin"}

    id = mapped_column(ForeignKey("users.id"), primary_key=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(50))

    last_name: Mapped[Optional[str]] = mapped_column(String(50))

    phone_number: Mapped[Optional[str]] = mapped_column(String(50))

    # A RESORT HAS AT MOST ONE ADMIN. THIS IS NULL FOR AN ADMIN THAT WAS REMOVED FROM THEIR RESORT.
    # THE ORGANIZATION OF THE ADMIN IS THE ORGANIZATION OF THEIR RESORT.

    resort_id: Mapped[Optional[int]] = mapped_column(ForeignKey("resorts.id"), unique=True)

    profile_picture: Mapped[Optional[str]] = mapped_column(String(256))

    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column()

    active_token: Mapped[Optional[str]] = mapped_column(Text)

    # RELATIONSHIP

    verification: Mapped["manager_verification.ManagerVerification"] = relationship(uselist=False, cascade="all")
