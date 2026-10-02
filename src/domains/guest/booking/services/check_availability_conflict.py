from datetime import date

from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from core.models.resort_availability import ResortAvailability, ResortAvailabilityStatus
from domains.guest.booking.services.get_booking_dates import get_booking_dates
from domains.guest.enums import GuestErrorMessage


def check_availability_conflict(session: Session, resort_id: int, check_in_date: date, check_out_date: date):

    conflict = session.scalars(
        select(ResortAvailability)
        .where(
            and_(
                ResortAvailability.resort_id == resort_id,
                ResortAvailability.date.in_(get_booking_dates(check_in_date, check_out_date)),
                ResortAvailability.status.in_(
                    [
                        ResortAvailabilityStatus.BOOKED,
                        ResortAvailabilityStatus.BLOCKED,
                        ResortAvailabilityStatus.MAINTENANCE,
                    ]
                ),
            )
        )
        .limit(1)
    ).one_or_none()

    if conflict:
        raise HTTPException(status_code=400, detail=GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name)
