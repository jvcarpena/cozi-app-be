from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, AuditMixin
from core.models import admin
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class ManagerVerification(Base, AuditMixin):

    __tablename__ = "manager_verifications"

    # THE MANAGER IS AN ADMIN (ONE RESORT), SO THIS POINTS TO THE ADMINS TABLE.

    manager_id: Mapped[str] = mapped_column(ForeignKey("admins.id"), primary_key=True)

    latest_email_sent_at: Mapped[datetime] = mapped_column(UTCDateTime)

    verified_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    # RELATIONSHIP

    manager: Mapped["admin.Admin"] = relationship(back_populates="verification")
