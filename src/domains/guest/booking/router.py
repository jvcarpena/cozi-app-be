from typing import Annotated

from fastapi import APIRouter, Depends

from domains.guest.booking.cancel_booking_service import cancel_booking
from domains.guest.booking.create_booking_service import CreateBookingContext, create_booking
from domains.guest.booking.get_booking_details_service import get_booking_details
from domains.guest.booking.get_booking_history_service import get_booking_history

booking_router = APIRouter(prefix="/bookings")


@booking_router.post("/preview")
def do_create_booking_preview():
    pass


@booking_router.post("")
def do_create_booking(context: Annotated[CreateBookingContext, Depends()]):

    return create_booking(context)


@booking_router.get("")
def do_get_booking_history():

    return get_booking_history()


@booking_router.get("/{booking_id}")
def do_get_booking_details():

    return get_booking_details()


@booking_router.get("/{booking_id}")
def do_cancel_booking():

    return cancel_booking()
