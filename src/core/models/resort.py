from decimal import Decimal
from enum import StrEnum
from typing import Optional

from sqlalchemy import String, Text, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import Base, AuditMixin


class ResortStatusEnum(StrEnum):

    AVAILABLE = "AVAILABLE"

    BOOKED = "BOOKED"

    MAINTENANCE = "MAINTENANCE"


class Resort(Base, AuditMixin):

    __tablename__ = "resorts"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    organization_id: Mapped[int] = mapped_column()

    name: Mapped[str] = mapped_column(String(256))

    status: Mapped[ResortStatusEnum] = mapped_column(String(24), index=True)

    description: Mapped[str] = mapped_column(Text)

    base_price_per_night: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    currency: Mapped[str] = mapped_column(String(10))

    max_guests: Mapped[int] = mapped_column()

    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 20))

    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 20))

    address: Mapped[str] = mapped_column(Text)
