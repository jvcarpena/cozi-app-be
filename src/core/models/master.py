from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import user
from core.models import manager_verification
from core.models import organization


class Master(user.User):
    """
    The owner of an organization. Whoever signs up as a manager becomes a master, and can own one or many resorts.
    A master can do everything an admin can, and also creates the resorts, sets their prices and invites the admins.
    """

    __tablename__ = "masters"

    __mapper_args__ = {"polymorphic_identity": "master"}

    id = mapped_column(ForeignKey("users.id"), primary_key=True)

    first_name: Mapped[Optional[str]] = mapped_column(String(50))

    last_name: Mapped[Optional[str]] = mapped_column(String(50))

    phone_number: Mapped[Optional[str]] = mapped_column(String(50))

    # ONE ORGANIZATION PER MASTER. THE RESORTS OF THE MASTER ARE THE RESORTS OF THE ORGANIZATION.

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"), unique=True)

    active_token: Mapped[Optional[str]] = mapped_column(Text)

    # RELATIONSHIPS

    organization: Mapped["organization.Organization"] = relationship()

    verification: Mapped["manager_verification.ManagerVerification"] = relationship(uselist=False, cascade="all")
