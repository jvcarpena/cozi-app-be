from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import HTTPException, Body, Path
from pydantic import BaseModel
from sqlalchemy import select, and_, delete

from core.models.booking import Booking, BookingStatusEnum
from core.models.resort_availability import ResortAvailability, ResortAvailabilityStatus
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoGuestUser
from domains.guest.enums import GuestErrorMessage


class CancelBookingRequestDTO(BaseModel):
    reason: str | None


@dataclass
class CancelBookingContext:
    user: AutoGuestUser
    session: AutoSession
    booking_id: Annotated[int, Path(...)]
    request_dto: Annotated[CancelBookingRequestDTO, Body()]


def cancel_booking(context: CancelBookingContext):

    booking = context.session.scalars(
        select(Booking).where(
            and_(
                Booking.id == context.booking_id,
                Booking.guest_id == context.user.id,
            )
        )
    ).one_or_none()

    if not booking:
        raise HTTPException(status_code=404, detail=GuestErrorMessage.BOOKING_DOES_NOT_EXIST.name)

    # CANCELLING AN ALREADY CANCELLED BOOKING CHANGES NOTHING

    if booking.status == BookingStatusEnum.CANCELLED:
        return

    booking.status = BookingStatusEnum.CANCELLED

    booking.cancelled_at = datetime.now(timezone.utc)

    booking.cancel_reason = context.request_dto.reason

    # FREE THE DATES THIS BOOKING WAS HOLDING

    context.session.execute(
        delete(ResortAvailability).where(
            and_(
                ResortAvailability.booking_id == booking.id,
                ResortAvailability.status == ResortAvailabilityStatus.BOOKED,
            )
        )
    )

    context.session.commit()

    return
