import bcrypt
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.services.auth_token_handler import AuthTokenHandler
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedLoginDataDTO
from domains.manager.enums import ManagerErrorMessage


class ManagerLoginResponseDTO(BaseModel):

    manager_id: str

    email_address: EmailStr

    first_name: str

    last_name: str

    phone_number: str | None = None

    token: str


def login(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedLoginDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload()

    # GET MANAGER OBJECT FROM THE DB

    manager = session.scalars(
        select(Admin).where(
            Admin.email_address == decrypted_user_data.email,
        )
    ).one_or_none()

    # CHECK IF MANAGER EXISTS

    if not manager:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.EMAIL_NOT_EXISTS.name)

    # CHECK IF MANAGER IS VERIFIED

    if manager.verification.verified_at is None:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.EMAIL_NOT_VERIFIED.name)

    # CHECK IF THE PASSWORD GIVEN IS CORRECT

    if not bcrypt.checkpw(decrypted_user_data.password.encode("utf-8"), manager.hashed_password):

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.INVALID_CREDENTIALS.name)

    # GENERATE TOKEN

    token = AuthTokenHandler(user_id=manager.id).generate_auth_token()

    # CREATE RESPONSE

    response = ManagerLoginResponseDTO(
        manager_id=manager.id,
        email_address=manager.email_address,
        first_name=manager.first_name,
        last_name=manager.last_name,
        phone_number=manager.phone_number,
        token=token,
    )

    return response
