import random

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest import Guest
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO
from domains.guest.enums import GuestErrorMessage


def generate_unique_guest_id(session: Session):

    guest_ids = session.scalars(select(Guest.id)).all()

    while True:

        generated_guest_id = "".join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(10))

        if generated_guest_id not in guest_ids:

            return generated_guest_id


def sign_up(encrypted_data: EncryptedDataDTO, session: Session):

    decrypted_user_data = SecurePayloadHandler(data_to_decrypt=encrypted_data.model_dump()).decrypt_payload(
        is_sign_up=True
    )

    existing_guest = session.scalars(
        select(Guest).where(
            Guest.email_address == decrypted_user_data.email,
        )
    ).one_or_none()

    if existing_guest:
        raise HTTPException(status_code=400, detail=GuestErrorMessage.EMAIL_REGISTERED.name)

    # GENERATE UNIQUE ID FOR NEW GUEST
    guest_id = generate_unique_guest_id(session)

    # ADD NEW GUEST DATA TO DB
    session.add(
        Guest(
            id=guest_id,
            email_address=decrypted_user_data.email,
            first_name=decrypted_user_data.first_name,
            last_name=decrypted_user_data.last_name,
            hashed_password=bcrypt.hashpw(decrypted_user_data.password.encode("utf-8"), bcrypt.gensalt()),
        )
    )

    session.commit()

    return
