from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.manager.auth.login_service import ManagerLoginResponseDTO, login
from domains.manager.auth.logout_service import logout
from domains.manager.auth.sign_up_service import sign_up
from domains.manager.auth.verify_manager_service import verify_manager

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

VERIFY_URL = "/manager/auth/verify"

auth_router = APIRouter(prefix="/auth")


@auth_router.post("/signup")
def do_sign_up(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession):

    return sign_up(encrypted_data, session)


@auth_router.get("/verify", response_class=HTMLResponse)
def do_get_verification_page(request: Request, d: str):

    return templates.TemplateResponse(
        "verify_account.html",
        {
            "request": request,
            "token": d,
            "verify_url": VERIFY_URL,
        },
    )


@auth_router.post("/verify")
def do_verify_manager(request: Request, data: Annotated[str, Form()], session: AutoSession):

    verify_manager(EncryptedDataDTO(data=data), session)

    return templates.TemplateResponse(
        "verified_account.html",
        {
            "request": request,
        },
    )


@auth_router.post("/login")
def do_login(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession) -> ManagerLoginResponseDTO:

    return login(encrypted_data, session)


@auth_router.post("/logout")
def do_logout(manager: AutoManagerUser):

    return logout(manager)
