from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any, Optional

from sqlalchemy import ForeignKey, String, Numeric, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class BookingStatusEnum(StrEnum):

    PENDING = "PENDING"

    CONFIRMED = "CONFIRMED"

    COMPLETED = "COMPLETED"

    CANCELLED = "CANCELLED"

    EXPIRED = "EXPIRED"


class Booking(Base, AuditMixin):

    __tablename__ = "bookings"

    __table_args__ = (Index("booking_table_index", "status", "check_in", "check_out"),)

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    guest_id: Mapped[Any] = mapped_column(ForeignKey("guests.id"))

    resort_id: Mapped[Any] = mapped_column(ForeignKey("resorts.id"))

    status: Mapped[BookingStatusEnum] = mapped_column(String(24))

    check_in: Mapped[datetime] = mapped_column(UTCDateTime)

    check_out: Mapped[datetime] = mapped_column(UTCDateTime)

    num_guests: Mapped[int] = mapped_column()

    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    currency: Mapped[str] = mapped_column(String(24))

    special_request: Mapped[Optional[str]] = mapped_column(Text)

    cancelled_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)

    cancel_reason: Mapped[Optional[str]] = mapped_column(Text)
