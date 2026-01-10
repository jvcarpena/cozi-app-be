from fastapi import APIRouter

from domains.guest.service_login import InitialResponseDTO, login

guest_router = APIRouter(prefix="/guest")


@guest_router.get("/login")
def do_login() -> InitialResponseDTO:
    return login()
