from typing import Annotated

from fastapi import APIRouter, Body

from core.services.auto_session import AutoSession
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.guest.login_service import InitialResponseDTO, login
from domains.guest.sign_up_service import sign_up

guest_router = APIRouter(prefix="/guest")


@guest_router.get("/login")
def do_login() -> InitialResponseDTO:

    return login()


@guest_router.post("/sign-up")
def do_sign_up(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession):

    return sign_up(encrypted_data, session)
