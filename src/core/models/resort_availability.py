from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import Optional

from sqlalchemy import ForeignKey, Numeric, String, Date
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base


class ResortAvailabilityStatus(StrEnum):

    BOOKED = "BOOKED"

    BLOCKED = "BLOCKED"

    MAINTENANCE = "MAINTENANCE"


class ResortAvailability(Base, AuditMixin):

    __tablename__ = "resort_availabilities"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    resort_id: Mapped[int] = mapped_column(ForeignKey("resorts.id"))

    booking_id: Mapped[Optional[int]] = mapped_column(ForeignKey("bookings.id"))

    date: Mapped[date] = mapped_column(Date)

    override_price: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 4))

    status: Mapped[ResortAvailabilityStatus] = mapped_column(String(24))
