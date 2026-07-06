from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated

from fastapi import Body, HTTPException
from pydantic import BaseModel, AwareDatetime, model_validator
from core.services.auto_session import AutoSession
from domains.guest.booking.services.check_availability_conflict import check_availability_conflict
from domains.guest.booking.services.compute_booking_price import compute_booking_price
from domains.guest.booking.services.get_active_resort import get_active_resort
from domains.guest.booking.services.validate_guest_capacity import validate_guest_capacity
from domains.guest.enums import GuestErrorMessage


class CreateBookingPreviewRequestDTO(BaseModel):
    resort_id: int
    check_in: AwareDatetime
    check_out: AwareDatetime
    num_guests: int

    @model_validator(mode="after")
    def validate_fields(self) -> "CreateBookingPreviewRequestDTO":
        if self.check_out <= self.check_in:
            raise HTTPException(status_code=422, detail=GuestErrorMessage.CHECKOUT_MUST_BE_AFTER_CHECK_IN.name)
        if self.num_guests < 1:
            raise HTTPException(status_code=422, detail=GuestErrorMessage.NUM_GUEST_MUST_BE_AT_LEAST_1.name)
        return self


@dataclass
class CreateBookingPreviewContext:
    session: AutoSession
    request_dto: Annotated[CreateBookingPreviewRequestDTO, Body()]


class CreateBookingPreviewResponseDTO(BaseModel):
    resort_id: int
    resort_name: str
    check_in: AwareDatetime
    check_out: AwareDatetime
    duration_hours: float
    booking_type: str
    nights: int | None
    total_price: Decimal
    currency: str


def create_booking_preview(context: CreateBookingPreviewContext) -> CreateBookingPreviewResponseDTO:

    resort = get_active_resort(context.session, context.request_dto.resort_id)

    validate_guest_capacity(resort, context.request_dto.num_guests)

    check_in_date = context.request_dto.check_in.date()

    check_out_date = context.request_dto.check_out.date()

    check_availability_conflict(context.session, context.request_dto.resort_id, check_in_date, check_out_date)

    duration_hours = (context.request_dto.check_out - context.request_dto.check_in).total_seconds() / 3600

    booking_type, nights, total_price = compute_booking_price(resort, duration_hours)

    return CreateBookingPreviewResponseDTO(
        resort_id=resort.id,
        resort_name=resort.name,
        check_in=context.request_dto.check_in,
        check_out=context.request_dto.check_out,
        duration_hours=duration_hours,
        booking_type=booking_type,
        nights=nights,
        total_price=total_price,
        currency=resort.currency,
    )
