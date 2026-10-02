from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import HTTPException, Body, Path
from pydantic import BaseModel
from sqlalchemy import select, and_

from core.models.booking import Booking
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

    booking.cancelled_at = datetime.now(timezone.utc)

    booking.cancel_reason = context.request_dto.reason

    context.session.commit()

    return
