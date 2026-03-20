import random
from datetime import datetime, timezone, timedelta

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest import Guest
from core.models.guest_verification import GuestVerification
from core.services.secure_payload_handler import SecurePayloadHandler
from core.services.send_email import send_email, SendEmailRequestDTO
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedSignUpDataDTO
from domains.guest.enums import GuestErrorMessage


def generate_unique_guest_id(session: Session):

    guest_ids = session.scalars(select(Guest.id)).all()

    while True:

        generated_guest_id = "".join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(10))

        if generated_guest_id not in guest_ids:

            return generated_guest_id


def sign_up(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedSignUpDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.model_dump()
    ).decrypt_payload(is_sign_up=True)

    # GET EXISTING USER FROM THE DB

    existing_user = session.scalars(
        select(Guest).where(
            Guest.email_address == decrypted_user_data.email,
        )
    ).one_or_none()

    # CHECK IF THE GUEST IS ALREADY VERIFIED

    if existing_user:

        # IF VERIFIED, RAISE EMAIL REGISTERED ERROR
        if existing_user.verification.verified_at:

            raise HTTPException(status_code=400, detail=GuestErrorMessage.EMAIL_REGISTERED.name)

        # IF NOT VERIFIED, CHECK IF THE LAST EMAIL SENT IS 24 HOURS AGO
        else:

            # IF YES, RESEND VERIFICATION EMAIL
            if existing_user.verification.latest_email_sent_at < datetime.now(tz=timezone.utc) - timedelta(hours=24):

                send_email(
                    SendEmailRequestDTO(
                        to=existing_user.email_address,
                        subject="Email Verification",
                        template_name="sign_up_email.html",
                        html_substitutions={
                            "verification_url": "",
                            "user_name": decrypted_user_data.first_name,
                        },
                    )
                )

                # UPDATE USER DATA JUST IN CASE THE USER CHANGED SOME DATA
                # UPON SIGNING UP USING THE SAME EMAIL.

                existing_user.first_name = decrypted_user_data.first_name

                existing_user.last_name = decrypted_user_data.last_name

                existing_user.phone_number = decrypted_user_data.phone

                existing_user.hashed_password = bcrypt.hashpw(
                    decrypted_user_data.password.encode("utf-8"), bcrypt.gensalt()
                )

                existing_user.verification.latest_email_sent_at = datetime.now(tz=timezone.utc)

                session.commit()

                return

            # IF NOT, RAISE CHECK YOUR EMAIL ERROR
            else:

                raise HTTPException(status_code=400, detail=GuestErrorMessage.CHECK_YOUR_EMAIL.name)

    # IF NO EXISTING USER, SEND VERIFICATION EMAIL

    send_email(
        SendEmailRequestDTO(
            to=decrypted_user_data.email,
            subject="Email Verification",
            template_name="sign_up_email.html",
            html_substitution={
                "verification_url": "",
                "user_name": decrypted_user_data.first_name,
            },
        )
    )

    # GENERATE UNIQUE ID

    guest_id = generate_unique_guest_id(session)

    # INSERT INTO GUEST TABLE

    session.add(
        new_guest := Guest(
            id=guest_id,
            email_address=decrypted_user_data.email,
            first_name=decrypted_user_data.first_name,
            last_name=decrypted_user_data.last_name,
            hashed_password=bcrypt.hashpw(decrypted_user_data.password.encode("utf-8"), bcrypt.gensalt()),
            phone_number=decrypted_user_data.phone,
        )
    )

    # INSERT INTO GUEST VERIFICATION TABLE

    session.add(
        GuestVerification(
            guest_id=new_guest.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
        )
    )

    session.commit()

    return
