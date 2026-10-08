from decimal import Decimal
from enum import StrEnum
from typing import Optional, List

from sqlalchemy import ForeignKey, String, Text, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models import resort_amenity, resort_review
from core.models.base import Base, AuditMixin


class ResortStatusEnum(StrEnum):

    ACTIVE = "ACTIVE"

    INACTIVE = "INACTIVE"

    MAINTENANCE = "MAINTENANCE"


class Resort(Base, AuditMixin):

    __tablename__ = "resorts"

    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_resorts_organization_id_name"),)

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))

    name: Mapped[str] = mapped_column(String(256))

    status: Mapped[ResortStatusEnum] = mapped_column(String(24), index=True)

    description: Mapped[str] = mapped_column(Text)

    base_price_per_night: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    base_price_per_day_use: Mapped[Decimal] = mapped_column(Numeric(12, 4))

    currency: Mapped[str] = mapped_column(String(10))

    max_guests: Mapped[int] = mapped_column()

    num_bedrooms: Mapped[int] = mapped_column()

    num_bathrooms: Mapped[int] = mapped_column()

    latitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 20))

    longitude: Mapped[Optional[Decimal]] = mapped_column(Numeric(30, 20))

    address: Mapped[str] = mapped_column(Text)

    # RELATIONSHIPS

    amenities: Mapped[List["resort_amenity.ResortAmenity"]] = relationship()

    reviews: Mapped[List["resort_review.ResortReview"]] = relationship()
