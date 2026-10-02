from dataclasses import dataclass
from datetime import timezone
from decimal import Decimal
from typing import Optional, Annotated
from zoneinfo import ZoneInfo

from fastapi import Body, HTTPException
from pydantic import BaseModel, AwareDatetime, model_validator

from core.models.booking import Booking, BookingStatusEnum
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoGuestUser
from domains.guest.booking.services.check_availability_conflict import check_availability_conflict
from domains.guest.booking.services.compute_booking_price import compute_booking_price
from domains.guest.booking.services.get_active_resort import get_active_resort
from domains.guest.booking.services.validate_guest_capacity import validate_guest_capacity
from domains.guest.enums import GuestErrorMessage


class CreateBookingRequestDTO(BaseModel):
    resort_id: int
    check_in: AwareDatetime
    check_out: AwareDatetime
    num_guests: int
    special_request: Optional[str] = None

    @model_validator(mode="after")
    def validate_fields(self) -> "CreateBookingRequestDTO":
        if self.check_out <= self.check_in:
            raise HTTPException(status_code=422, detail=GuestErrorMessage.CHECKOUT_MUST_BE_AFTER_CHECK_IN.name)
        if self.num_guests < 1:
            raise HTTPException(status_code=422, detail=GuestErrorMessage.NUM_GUEST_MUST_BE_AT_LEAST_1.name)
        return self


@dataclass
class CreateBookingContext:
    user: AutoGuestUser
    session: AutoSession
    request_dto: Annotated[CreateBookingRequestDTO, Body()]


class CreateBookingResponseDTO(BaseModel):
    id: int
    resort_id: int
    resort_name: str
    status: BookingStatusEnum
    check_in: AwareDatetime
    check_out: AwareDatetime
    duration_hours: float
    booking_type: str
    nights: int | None
    num_guests: int
    total_price: Decimal
    currency: str
    special_request: str | None
    created_at: AwareDatetime


def create_booking(context: CreateBookingContext) -> CreateBookingResponseDTO:

    resort = get_active_resort(context.session, context.request_dto.resort_id)

    validate_guest_capacity(resort, context.request_dto.num_guests)

    check_in_date = context.request_dto.check_in.date()

    check_out_date = context.request_dto.check_out.date()

    check_availability_conflict(context.session, context.request_dto.resort_id, check_in_date, check_out_date)

    duration_hours = (context.request_dto.check_out - context.request_dto.check_in).total_seconds() / 3600

    booking_type, nights, total_price = compute_booking_price(resort, duration_hours)

    context.session.add(
        booking := Booking(
            guest_id=context.user.id,
            resort_id=resort.id,
            status=BookingStatusEnum.PENDING,
            check_in=context.request_dto.check_in.astimezone(timezone.utc),
            check_out=context.request_dto.check_out.astimezone(timezone.utc),
            num_guests=context.request_dto.num_guests,
            nights=nights if nights else None,
            total_price=total_price,
            currency=resort.currency,
            special_request=context.request_dto.special_request,
        )
    )

    context.session.commit()

    return CreateBookingResponseDTO(
        id=booking.id,
        resort_id=resort.id,
        resort_name=resort.name,
        status=booking.status,
        check_in=context.request_dto.check_in,
        check_out=context.request_dto.check_out,
        duration_hours=duration_hours,
        booking_type=booking_type,
        nights=nights,
        num_guests=booking.num_guests,
        total_price=total_price,
        currency=booking.currency,
        special_request=booking.special_request,
        created_at=booking.created_at.astimezone(ZoneInfo("Asia/Manila")),
    )
