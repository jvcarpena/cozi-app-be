from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.templating import Jinja2Templates

from core.services.auto_session import AutoSession, AsyncAutoSession
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.guest.login_service import LoginResponseDTO, login
from domains.guest.logout_service import logout
from domains.guest.sign_up_service import sign_up
from domains.guest.verify_guest_service import verify_guest

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


guest_router = APIRouter(prefix="/guest")


@guest_router.post("/sign-up")
def do_sign_up(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession):

    return sign_up(encrypted_data, session)


@guest_router.get("/verification", response_class=HTMLResponse)
def do_get_verification_page(request: Request, d: str):

    return templates.TemplateResponse(
        "verify_account.html",
        {
            "request": request,
            "token": d,
        },
    )


@guest_router.post("/verification")
def do_verify_guest(request: Request, data: Annotated[str, Form()], session: AutoSession):

    verify_guest(EncryptedDataDTO(data=data), session)

    return templates.TemplateResponse(
        "verified_account.html",
        {
            "request": request,
        },
    )


@guest_router.post("/login")
def do_login(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession) -> LoginResponseDTO:

    return login(encrypted_data, session)


@guest_router.post("/logout")
def do_logout(auth_token: Annotated[str, Depends(APIKeyHeader(name="Authorization"))]):

    return logout(auth_token)
