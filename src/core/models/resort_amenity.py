from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class ResortAmenityCategoryEnum(StrEnum):

    POOL = "POOL"

    ENTERTAINMENT = "ENTERTAINMENT"

    DINING = "DINING"

    UTILITIES = "UTILITIES"


class ResortAmenity(Base, AuditMixin):

    __tablename__ = "resort_amenities"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    resort_id: Mapped[int] = mapped_column(ForeignKey("resorts.id"), index=True)

    category: Mapped[ResortAmenityCategoryEnum] = mapped_column(String(24))

    name: Mapped[str] = mapped_column(String(256))

    unavailable_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
