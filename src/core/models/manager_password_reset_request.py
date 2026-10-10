from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import Integer, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base, AuditMixin
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class ManagerLinkPurpose(StrEnum):
    """
    What the emailed link is for. Both open the same page where a password is chosen, but an invite is sent to an
    admin who has no password yet and lives longer than a password reset.
    """

    RESET = "RESET"

    INVITE = "INVITE"


class ManagerPasswordResetRequest(Base, AuditMixin):

    __tablename__ = "manager_password_reset_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # MASTERS AND ADMINS CAN BOTH RESET A PASSWORD, SO THIS POINTS TO THE SHARED USERS TABLE.

    manager_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)

    purpose: Mapped[str] = mapped_column(String(24), default=ManagerLinkPurpose.RESET, server_default="RESET")

    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)

    request_consumed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
