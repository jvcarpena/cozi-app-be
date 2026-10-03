from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base, AuditMixin
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class ManagerVerification(Base, AuditMixin):

    __tablename__ = "manager_verifications"

    # MASTERS AND ADMINS BOTH NEED TO BE VERIFIED, SO THIS POINTS TO THE SHARED USERS TABLE.

    manager_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)

    latest_email_sent_at: Mapped[datetime] = mapped_column(UTCDateTime)

    verified_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
