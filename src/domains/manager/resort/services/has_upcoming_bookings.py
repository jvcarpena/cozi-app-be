from datetime import datetime, timezone

from sqlalchemy import select, exists, and_
from sqlalchemy.orm import Session

from core.models.booking import Booking, BookingStatusEnum


def has_upcoming_bookings(session: Session, resort_id: int) -> bool:
    """
    True if a guest still has a PENDING or CONFIRMED booking at the resort that has not ended yet.
    Cancelled, expired and completed bookings, and bookings in the past, do not count.
    """

    return session.scalars(
        select(
            exists().where(
                and_(
                    Booking.resort_id == resort_id,
                    Booking.status.in_([BookingStatusEnum.PENDING, BookingStatusEnum.CONFIRMED]),
                    Booking.check_out > datetime.now(tz=timezone.utc),
                )
            )
        )
    ).one()
