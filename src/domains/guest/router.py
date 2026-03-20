from typing import Annotated

from fastapi import APIRouter, Body, Depends
from fastapi.security import APIKeyHeader

from core.services.auto_session import AutoSession
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.guest.login_service import LoginResponseDTO, login
from domains.guest.logout_service import logout
from domains.guest.sign_up_service import sign_up
from domains.guest.verify_guest_service import verify_guest

guest_router = APIRouter(prefix="/guest")


@guest_router.post("/sign-up")
def do_sign_up(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession):

    return sign_up(encrypted_data, session)


@guest_router.post("/verification")
def do_verify_guest(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession):

    return verify_guest(encrypted_data, session)


@guest_router.post("/login")
def do_login(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession) -> LoginResponseDTO:

    return login(encrypted_data, session)


@guest_router.post("/logout")
def do_logout(auth_token: Annotated[str, Depends(APIKeyHeader(name="Authorization"))]):

    return logout(auth_token)
