from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base
from core.tools.sqlalchemy.utc_date_time import UTCDateTime


class ResortRoomTypeEnum(StrEnum):

    STANDARD_ROOM = "STANDARD_ROOM"

    SUITE = "SUITE"


class ResortRoom(Base, AuditMixin):

    __tablename__ = "resort_rooms"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    resort_id: Mapped[int] = mapped_column(ForeignKey("resorts.id"), index=True)

    name: Mapped[str] = mapped_column(String(256))

    type: Mapped[ResortRoomTypeEnum] = mapped_column(String(24))

    capacity: Mapped[int] = mapped_column()

    description: Mapped[str] = mapped_column(Text)

    unavailable_at: Mapped[Optional[datetime]] = mapped_column(UTCDateTime)
