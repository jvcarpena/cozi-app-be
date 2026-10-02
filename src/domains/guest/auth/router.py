from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.templating import Jinja2Templates

from core.services.auto_session import AutoSession
from domains.guest.auth.get_active_password_reset_request import get_active_password_reset_request
from domains.guest.auth.initiate_password_reset import initiate_password_reset, InitiatePasswordResetResponseDTO
from domains.guest.auth.login_service import LoginResponseDTO, login
from domains.guest.auth.logout_service import logout
from domains.guest.auth.reset_password import reset_password
from domains.guest.auth.sign_up_service import sign_up
from domains.guest.auth.verify_guest_service import verify_guest
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.guest.enums import GuestErrorMessage

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

auth_router = APIRouter(prefix="/auth")

RESET_PASSWORD_URL = "/guest/auth/reset-password"

# ERRORS THAT CAN BE FIXED BY RETYPING THE PASSWORD, THE FORM IS SHOWN AGAIN WITH THE MESSAGE.

PASSWORD_FORM_ERRORS = {
    GuestErrorMessage.PASSWORD_MISMATCH.name: GuestErrorMessage.PASSWORD_MISMATCH.value,
    GuestErrorMessage.INVALID_PASSWORD_LENGTH.name: GuestErrorMessage.INVALID_PASSWORD_LENGTH.value,
}


@auth_router.post("/sign-up")
def do_sign_up(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession):

    return sign_up(encrypted_data, session)


@auth_router.get("/verification", response_class=HTMLResponse)
def do_get_verification_page(request: Request, d: str):

    return templates.TemplateResponse(
        "verify_account.html",
        {
            "request": request,
            "token": d,
        },
    )


@auth_router.post("/verification")
def do_verify_guest(request: Request, data: Annotated[str, Form()], session: AutoSession):

    verify_guest(EncryptedDataDTO(data=data), session)

    return templates.TemplateResponse(
        "verified_account.html",
        {
            "request": request,
        },
    )


@auth_router.post("/login")
def do_login(encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession) -> LoginResponseDTO:

    return login(encrypted_data, session)


@auth_router.post("/logout")
def do_logout(auth_token: Annotated[str, Depends(APIKeyHeader(name="Authorization"))]):

    return logout(auth_token)


@auth_router.post("/forgot-password")
def do_initiate_password_reset(
    encrypted_data: Annotated[EncryptedDataDTO, Body()], session: AutoSession
) -> InitiatePasswordResetResponseDTO:

    return initiate_password_reset(encrypted_data, session)


@auth_router.get("/reset-password", response_class=HTMLResponse)
def do_get_reset_password_page(request: Request, d: str, session: AutoSession):

    # CHECK THE LINK FIRST SO AN EXPIRED OR USED LINK IS SHOWN RIGHT AWAY, NOT AFTER THE GUEST TYPES A PASSWORD.

    try:

        get_active_password_reset_request(d, session)

    except HTTPException:

        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "is_link_valid": False,
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        "reset_password.html",
        {
            "request": request,
            "is_link_valid": True,
            "token": d,
            "reset_url": RESET_PASSWORD_URL,
        },
    )


@auth_router.post("/reset-password", response_class=HTMLResponse)
def do_reset_password(
    request: Request,
    token: Annotated[str, Form()],
    new_password: Annotated[str, Form()],
    confirm_password: Annotated[str, Form()],
    session: AutoSession,
):

    try:

        reset_password(token, new_password, confirm_password, session)

    except HTTPException as exception:

        # A PASSWORD PROBLEM SHOWS THE FORM AGAIN, ANYTHING ELSE MEANS THE LINK CAN NO LONGER BE USED.

        if exception.detail in PASSWORD_FORM_ERRORS:

            return templates.TemplateResponse(
                "reset_password.html",
                {
                    "request": request,
                    "is_link_valid": True,
                    "token": token,
                    "reset_url": RESET_PASSWORD_URL,
                    "error_message": PASSWORD_FORM_ERRORS[exception.detail],
                },
                status_code=400,
            )

        return templates.TemplateResponse(
            "reset_password.html",
            {
                "request": request,
                "is_link_valid": False,
            },
            status_code=400,
        )

    return templates.TemplateResponse(
        "password_reset_success.html",
        {
            "request": request,
        },
    )
