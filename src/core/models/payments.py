from typing import Optional

from sqlalchemy import ForeignKey, String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base


class Payment(Base, AuditMixin):

    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    booking_id: Mapped[int] = mapped_column(ForeignKey("bookings.id"))

    payment_intent_amount: Mapped[int] = mapped_column()

    currency: Mapped[str] = mapped_column(String(24))

    payment_method: Mapped[str] = mapped_column(String(24))

    payment_intent_id: Mapped[str] = mapped_column(String(256), unique=True)

    client_key: Mapped[str] = mapped_column(String(256))

    paymongo_status: Mapped[str] = mapped_column(String(64))

    # OPTIONAL FIELDS

    payment_id: Mapped[Optional[str]] = mapped_column(String(256))

    net_amount: Mapped[Optional[float]] = mapped_column()

    fee: Mapped[Optional[float]] = mapped_column()

    balance_transaction_id: Mapped[Optional[str]] = mapped_column(String(256))

    source_id: Mapped[Optional[str]] = mapped_column(String(256))

    event_id: Mapped[Optional[str]] = mapped_column(String(256))

    payment_response: Mapped[Optional[dict]] = mapped_column(JSON(none_as_null=True))
