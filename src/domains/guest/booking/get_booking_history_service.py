from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Query
from pydantic import BaseModel, AwareDatetime
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from core.models.booking import BookingStatusEnum, Booking
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoUser


class BookingHistoryRequestDTO(BaseModel):
    status: BookingStatusEnum


@dataclass
class BookingHistoryContext:
    user: AutoUser
    session: AutoSession
    request_dto: Annotated[BookingHistoryRequestDTO, Query()]


class BookingHistoryDTO(BaseModel):
    id: int
    resort_name: str
    status: BookingStatusEnum
    check_in: AwareDatetime
    check_out: AwareDatetime
    num_guests: int
    total_price: Decimal
    currency: str
    created_at: AwareDatetime


class BookingHistoryResponseDTO(BaseModel):
    bookings: list[BookingHistoryDTO]


def get_booking_history(context: BookingHistoryContext) -> BookingHistoryResponseDTO:

    bookings = context.session.scalars(
        select(Booking)
        .options(selectinload(Booking.resort))
        .where(
            and_(
                Booking.guest_id == context.user.id,
                Booking.status == context.request_dto.status,
            )
        )
        .order_by(Booking.created_at.desc())
    ).all()

    bookings_dto: list[BookingHistoryDTO] = [
        BookingHistoryDTO(
            id=booking.id,
            resort_name=booking.resort.name,
            status=booking.status,
            check_in=booking.check_in.astimezone(ZoneInfo("Asia/Manila")),
            check_out=booking.check_out.astimezone(ZoneInfo("Asia/Manila")),
            num_guests=booking.num_guests,
            total_price=booking.total_price,
            currency=booking.currency,
            created_at=booking.created_at,
        )
        for booking in bookings
    ]

    return BookingHistoryResponseDTO(bookings=bookings_dto)
