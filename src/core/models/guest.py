from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import mapped_column, Mapped, relationship

from core.models import user
from core.models import guest_verification


class Guest(user.User):

    __tablename__ = "guests"

    __mapper_args__ = {
        "polymorphic_identity": "guest",
    }

    id = mapped_column(ForeignKey("users.id"), primary_key=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(50))

    last_name: Mapped[Optional[str]] = mapped_column(String(50))

    phone_number: Mapped[Optional[str]] = mapped_column(String(50))

    # RELATIONSHIP

    verification: Mapped["guest_verification.GuestVerification"] = relationship(
        back_populates="guest", uselist=False, cascade="all, delete-orphan"
    )
