from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest import Guest
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedSignUpDataDTO
from domains.guest.enums import GuestErrorMessage


def verify_guest(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedSignUpDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload(is_sign_up=True)

    # GET THE GUEST FROM THE DB AND CHECK IF THE GUEST EXISTS

    guest = session.scalars(
        select(Guest).where(
            Guest.email_address == decrypted_user_data.email,
        )
    ).one_or_none()

    if not guest:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.ACCOUNT_DOES_NOT_EXISTS.name)

    # CHECK IF THE EMAIL IS EXPIRED, IF EXPIRED RAISE LINK EXPIRED ERROR

    current_datetime_utc = datetime.now(tz=timezone.utc)

    is_expired = guest.verification.latest_email_sent_at < current_datetime_utc - timedelta(hours=24)

    if is_expired:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.LINK_EXPIRED.name)

    # IF NOT EXPIRED, UPDATE THE STATUS OF GUEST'S VERIFICATION

    guest.verification.verified_at = current_datetime_utc

    session.commit()

    return
