import os
from datetime import datetime, timezone, timedelta

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from core.services.password_reset_token_handler import MANAGER_PURPOSE, PasswordResetTokenHandler
from core.services.secure_payload_handler import SecurePayloadHandler
from core.services.send_email import SendEmailRequestDTO
from core.tools.celery.tasks.email_task import send_email_task
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedPasswordResetDTO

API_BASE_URL = os.environ.get("API_BASE_URL", "http://cozi-api.localhost")

PASSWORD_RESET_EXPIRY = timedelta(hours=1)

GENERIC_MESSAGE = "If the email is registered, a password reset link has been sent."


class InitiatePasswordResetResponseDTO(BaseModel):

    message: str = GENERIC_MESSAGE


def initiate_password_reset(encrypted_data: EncryptedDataDTO, session: Session):

    # ALWAYS RETURN THE SAME RESPONSE, WHETHER OR NOT THE EMAIL EXISTS, SO THE ENDPOINT
    # CANNOT BE USED TO FIND OUT WHICH EMAILS ARE REGISTERED.

    response = InitiatePasswordResetResponseDTO()

    decrypted_data: DecryptedPasswordResetDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload(is_password_reset=True)

    manager = session.scalars(select(Admin).where(Admin.email_address == decrypted_data.email)).one_or_none()

    # CHECK IF THE MANAGER EXISTS AND IS VERIFIED

    if not manager or manager.verification.verified_at is None:

        return response

    # CHECK IF THE MANAGER HAS A PASSWORD RESET REQUEST THAT IS NOT EXPIRED AND NOT CONSUMED,
    # IF YES, THE LINK THAT WAS ALREADY EMAILED IS STILL VALID SO DO NOT SEND ANOTHER ONE.

    most_recent_request = session.scalars(
        select(ManagerPasswordResetRequest)
        .where(ManagerPasswordResetRequest.manager_id == manager.id)
        .order_by(ManagerPasswordResetRequest.id.desc())
        .limit(1)
    ).one_or_none()

    current_datetime_utc = datetime.now(tz=timezone.utc)

    if (
        most_recent_request
        and not most_recent_request.request_consumed_at
        and most_recent_request.expires_at > current_datetime_utc
    ):

        return response

    # INSERT THE PASSWORD RESET REQUEST

    session.add(
        new_request := ManagerPasswordResetRequest(
            manager_id=manager.id,
            expires_at=current_datetime_utc + PASSWORD_RESET_EXPIRY,
        )
    )

    session.commit()

    # BUILD THE REQUEST TOKEN, IT IS SIGNED FOR MANAGERS ONLY SO A GUEST TOKEN CANNOT BE USED HERE.

    request_token = PasswordResetTokenHandler(
        request_id=new_request.id, expiry_date=new_request.expires_at, purpose=MANAGER_PURPOSE
    ).generate_reset_token()

    # SEND EMAIL TO MANAGER THE RESET PAGE WITH THE REQUEST TOKEN

    send_email_task.delay(
        SendEmailRequestDTO(
            to=manager.email_address,
            subject="Reset Your Password",
            template_name="password_reset_email.html",
            html_substitutions={
                "reset_url": f"{API_BASE_URL}/manager/auth/reset-password?d={request_token}",
                "user_name": manager.first_name,
            },
        ).model_dump()
    )

    return response
