from dataclasses import dataclass
from datetime import timezone
from typing import Optional, Annotated

from fastapi import Body, HTTPException
from pydantic import BaseModel, AwareDatetime
from sqlalchemy import select, and_

from core.models.booking import Booking
from core.models.resort import Resort
from core.models.resort_availability import ResortAvailability, ResortAvailabilityStatus
from core.services.auto_session import AutoSession
from domains.guest.enums import GuestErrorMessage


@dataclass
class CreateBookingContext:
    session: AutoSession
    request_dto: "Annotated[CreateBookingRequestDTO, Body()]"


class CreateBookingRequestDTO(BaseModel):
    guest_id: str
    resort_id: int
    check_in: AwareDatetime
    check_out: AwareDatetime
    num_guests: int
    special_request: Optional[str] = None


def create_booking(context: CreateBookingContext):

    # CHECK IF ANY DATE IN RANGE IS ALREADY BOOKED, BLOCKED, OR UNDER MAINTENANCE

    conflict = context.session.scalars(
        select(ResortAvailability)
        .where(
            and_(
                ResortAvailability.resort_id == context.request_dto.resort_id,
                ResortAvailability.date >= context.request_dto.check_in.date(),
                ResortAvailability.date < context.request_dto.check_out.date(),
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
        raise HTTPException(status_code=409, detail=GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name)

    # GET RESORT TO CHECK THE MAX CAPACITY OF GUEST

    resort = context.session.scalars(
        select(Resort).where(
            Resort.id == context.request_dto.resort_id,
        )
    ).one()

    if context.request_dto.num_guests > resort.max_guests:
        raise HTTPException(status_code=400, detail=GuestErrorMessage.NUMBER_OF_GUESTS_EXCEEDS_RESORT_CAPACITY.name)

    context.session.add(
        Booking(
            guest_id=context.request_dto.guest_id,
            check_in=context.request_dto.check_in.astimezone(timezone.utc),
            check_out=context.request_dto.check_out.astimezone(timezone.utc),
            num_guests=context.request_dto.num_guests,
            special_request=context.request_dto.special_request,
        )
    )

    context.session.commit()

    return
