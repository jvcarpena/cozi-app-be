import bcrypt
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest import Guest
from core.services.auth_token_handler import AuthTokenHandler
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedLoginDataDTO
from domains.guest.enums import GuestErrorMessage


class LoginResponseDTO(BaseModel):

    guest_id: str

    email_address: EmailStr

    first_name: str

    last_name: str

    phone_number: str

    token: str


def login(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedLoginDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.model_dump()
    ).decrypt_payload()

    # GET GUEST OBJECT FROM THE DB

    guest = session.scalars(
        select(Guest).where(
            Guest.email_address == decrypted_user_data.email,
        )
    ).one_or_none()

    # CHECK IF GUEST EXISTS

    if not guest:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.EMAIL_NOT_EXISTS.name)

    # CHECK IF GUEST IS VERIFIED

    if guest.verification.verified_at is None:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.EMAIL_NOT_VERIFIED.name)

    # CHECK IF THE PASSWORD GIVEN IS CORRECT

    if not bcrypt.checkpw(decrypted_user_data.password.encode("utf-8"), guest.hashed_password):

        raise HTTPException(status_code=400, detail=GuestErrorMessage.INVALID_CREDENTIALS.name)

    # GENERATE TOKEN

    token = AuthTokenHandler(user_id=guest.id).generate_auth_token()

    # CREATE RESPONSE

    response = LoginResponseDTO(
        user_id=guest.id,
        email_address=guest.email_address,
        first_name=guest.first_name,
        last_name=guest.last_name,
        phone_number=guest.phone_number,
        token=token,
    )

    return response
