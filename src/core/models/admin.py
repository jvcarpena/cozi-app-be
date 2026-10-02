from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import user
from core.models import manager_verification


class Admin(user.User):

    __tablename__ = "admins"

    __mapper_args__ = {"polymorphic_identity": "admin"}

    id = mapped_column(ForeignKey("users.id"), primary_key=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(50))

    last_name: Mapped[Optional[str]] = mapped_column(String(50))

    phone_number: Mapped[Optional[str]] = mapped_column(String(50))

    # AN ADMIN OWNS A SINGLE RESORT (OR MANAGES ONE FOR A MASTER). THESE ARE NULL AFTER SIGN-UP
    # AND ARE SET ONCE THE ADMIN ADDS THEIR RESORT.

    organization_id: Mapped[Optional[int]] = mapped_column()

    resort_id: Mapped[Optional[int]] = mapped_column()

    profile_picture: Mapped[Optional[str]] = mapped_column(String(256))

    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column()

    active_token: Mapped[Optional[str]] = mapped_column(Text)

    # RELATIONSHIP

    verification: Mapped["manager_verification.ManagerVerification"] = relationship(
        back_populates="manager", uselist=False, cascade="all, delete-orphan"
    )
