from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Path, HTTPException
from pydantic import BaseModel, AwareDatetime
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from core.models.booking import BookingStatusEnum, Booking
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoUser
from domains.guest.enums import GuestErrorMessage


@dataclass
class BookingDetailsContext:
    user: AutoUser
    session: AutoSession
    booking_id: "Annotated[int, Path(...)]"


class ResortDTO(BaseModel):
    id: int
    name: str
    address: str


class BookingDetailsResponseDTO(BaseModel):
    id: int
    resort: ResortDTO
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


def get_booking_details(context: BookingDetailsContext) -> BookingDetailsResponseDTO:

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

    duration_hours = (booking.check_out - booking.check_in).total_seconds() / 3600

    return BookingDetailsResponseDTO(
        id=booking.id,
        resort=ResortDTO(
            id=booking.resort_id,
            name=booking.resort.name,
            address=booking.resort.address,
        ),
        status=booking.status,
        check_in=booking.check_in.astimezone(ZoneInfo("Asia/Manila")),
        check_out=booking.check_out.astimezone(ZoneInfo("Asia/Manila")),
        duration_hours=duration_hours,
        booking_type="overnight" if booking.nights else "day_use",
        nights=booking.nights,
        num_guests=booking.num_guests,
        total_price=booking.total_price,
        currency=booking.currency,
        special_request=booking.special_request,
        created_at=booking.created_at.astimezone(ZoneInfo("Asia/Manila")),
    )
