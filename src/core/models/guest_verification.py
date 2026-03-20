from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base, AuditMixin
from core.models import guest
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class GuestVerification(Base, AuditMixin):

    __tablename__ = "guest_verifications"

    guest_id: Mapped[str] = mapped_column(ForeignKey("guests.id"), primary_key=True)

    latest_email_sent_at: Mapped[datetime] = mapped_column(UTCDateTime)

    verified_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    # RELATIONSHIP

    guest: Mapped["guest.Guest"] = relationship(back_populates="verification")
