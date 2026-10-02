from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base, AuditMixin
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class ManagerPasswordResetRequest(Base, AuditMixin):

    __tablename__ = "manager_password_reset_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # THE MANAGER IS AN ADMIN (ONE RESORT), SO THIS POINTS TO THE ADMINS TABLE.

    manager_id: Mapped[str] = mapped_column(ForeignKey("admins.id"), index=True)

    expires_at: Mapped[datetime] = mapped_column(UTCDateTime)

    request_consumed_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
