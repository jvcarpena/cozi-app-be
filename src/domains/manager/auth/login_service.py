import bcrypt
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from core.models.master import Master
from core.services.auth_token_handler import AuthTokenHandler
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedLoginDataDTO
from domains.manager.auth.get_manager_by_email import get_manager_by_email
from domains.manager.enums import ManagerErrorMessage


class ManagerLoginResponseDTO(BaseModel):

    manager_id: str

    # "master" OR "admin", THE CLIENT USES IT TO CHOOSE WHICH SCREENS TO SHOW.

    role: str

    email_address: EmailStr

    first_name: str

    last_name: str

    phone_number: str | None = None

    # A MASTER OWNS AN ORGANIZATION, AN ADMIN MANAGES ONE RESORT.

    organization_id: int | None = None

    organization_name: str | None = None

    resort_id: int | None = None

    token: str


def login(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedLoginDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload()

    # GET MANAGER OBJECT FROM THE DB

    manager = get_manager_by_email(session, decrypted_user_data.email)

    # CHECK IF MANAGER EXISTS

    if not manager:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.EMAIL_NOT_EXISTS.name)

    # CHECK IF MANAGER IS VERIFIED

    if manager.verification is None or manager.verification.verified_at is None:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.EMAIL_NOT_VERIFIED.name)

    # CHECK IF THE PASSWORD GIVEN IS CORRECT

    # AN ADMIN THAT WAS INVITED BUT HAS NOT SET A PASSWORD YET HAS NO PASSWORD TO CHECK.

    if manager.hashed_password is None or not bcrypt.checkpw(
        decrypted_user_data.password.encode("utf-8"), manager.hashed_password
    ):

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.INVALID_CREDENTIALS.name)

    # GENERATE TOKEN

    token = AuthTokenHandler(user_id=manager.id).generate_auth_token()

    # CREATE RESPONSE

    is_master = isinstance(manager, Master)

    response = ManagerLoginResponseDTO(
        manager_id=manager.id,
        role="master" if is_master else "admin",
        email_address=manager.email_address,
        first_name=manager.first_name,
        last_name=manager.last_name,
        phone_number=manager.phone_number,
        organization_id=manager.organization_id if is_master else None,
        organization_name=manager.organization.name if is_master else None,
        resort_id=None if is_master else manager.resort_id,
        token=token,
    )

    return response
