from typing import Any, Optional

from sqlalchemy import ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import AuditMixin, Base
from core.models import guest


class ResortReview(Base, AuditMixin):

    __tablename__ = "resort_reviews"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    resort_id: Mapped[int] = mapped_column(ForeignKey("resorts.id"), index=True)

    guest_id: Mapped[Any] = mapped_column(ForeignKey("guests.id"))

    overall_rating: Mapped[int] = mapped_column()

    cleanliness_rating: Mapped[int] = mapped_column()

    value_rating: Mapped[int] = mapped_column()

    comment: Mapped[Optional[str]] = mapped_column(Text)

    # RELATIONSHIP

    guest: Mapped["guest.Guest"] = relationship()
