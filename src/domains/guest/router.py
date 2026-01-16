from fastapi import APIRouter

from domains.guest.service_login import InitialResponseDTO, login
from domains.guest.service_sign_up import sign_up

guest_router = APIRouter(prefix="/guest")


@guest_router.get("/login")
def do_login() -> InitialResponseDTO:

    return login()


@guest_router.post("/sign-up")
def do_sign_up():

    return sign_up()
