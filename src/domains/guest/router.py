from fastapi import APIRouter

from domains.guest.auth.router import auth_router
from domains.guest.booking.router import booking_router
from domains.guest.resort.router import resort_router

guest_router = APIRouter(prefix="/guest")


(
    guest_router.include_router(auth_router),
    guest_router.include_router(resort_router),
    guest_router.include_router(booking_router),
)
