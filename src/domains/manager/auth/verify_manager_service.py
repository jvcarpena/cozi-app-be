from datetime import datetime, timezone, timedelta

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.master import Master
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.manager.dtos.sign_up_dto import DecryptedManagerSignUpDataDTO
from domains.manager.enums import ManagerErrorMessage


def verify_manager(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedManagerSignUpDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload(is_manager_sign_up=True)

    # GET THE MANAGER FROM THE DB AND CHECK IF THE MANAGER EXISTS

    manager = session.scalars(
        select(Master).where(
            Master.email_address == decrypted_user_data.email,
            Master.deleted_at.is_(None),
        )
    ).one_or_none()

    if not manager:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.ACCOUNT_DOES_NOT_EXISTS.name)

    # CHECK IF THE EMAIL IS EXPIRED, IF EXPIRED RAISE LINK EXPIRED ERROR

    current_datetime_utc = datetime.now(tz=timezone.utc)

    is_expired = manager.verification.latest_email_sent_at < current_datetime_utc - timedelta(hours=24)

    if is_expired:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.LINK_EXPIRED.name)

    # IF NOT EXPIRED, UPDATE THE STATUS OF MANAGER'S VERIFICATION

    manager.verification.verified_at = current_datetime_utc

    session.commit()

    return
