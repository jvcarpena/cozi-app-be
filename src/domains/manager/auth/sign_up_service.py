import os
from datetime import datetime, timezone, timedelta

import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.manager_verification import ManagerVerification
from core.services.secure_payload_handler import SecurePayloadHandler
from core.services.send_email import SendEmailRequestDTO
from core.services.user_id_generator import generate_user_id
from core.tools.celery.tasks.email_task import send_email_task
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, DecryptedSignUpDataDTO
from domains.manager.enums import ManagerErrorMessage

QUEUE_NAME = os.environ.get("EMAIL_NOTIF_QUEUE", "email_notif_queue_develop")


def sign_up(encrypted_data: EncryptedDataDTO, session: Session):

    # DECRYPT DATA

    decrypted_user_data: DecryptedSignUpDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload(is_sign_up=True)

    # GET EXISTING USER FROM THE DB

    existing_user = session.scalars(
        select(Admin).where(
            Admin.email_address == decrypted_user_data.email,
        )
    ).one_or_none()

    # CHECK IF THE MANAGER IS ALREADY VERIFIED

    if existing_user:

        # IF VERIFIED, RAISE EMAIL REGISTERED ERROR
        if existing_user.verification.verified_at:

            raise HTTPException(status_code=400, detail=ManagerErrorMessage.EMAIL_REGISTERED.name)

        # IF NOT VERIFIED, CHECK IF THE LAST EMAIL SENT IS 24 HOURS AGO
        else:

            # IF YES, RESEND VERIFICATION EMAIL
            if existing_user.verification.latest_email_sent_at < datetime.now(tz=timezone.utc) - timedelta(hours=24):

                send_email_task.delay(
                    SendEmailRequestDTO(
                        to=existing_user.email_address,
                        subject="Email Verification",
                        template_name="sign_up_email.html",
                        html_substitutions={
                            "verification_url": f"http://cozi-api.localhost/manager/auth/verify?d={encrypted_data.data}",
                            "user_name": decrypted_user_data.first_name,
                        },
                    ).model_dump()
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

                raise HTTPException(status_code=400, detail=ManagerErrorMessage.CHECK_YOUR_EMAIL.name)

    # IF NO EXISTING USER, SEND VERIFICATION EMAIL

    send_email_task.delay(
        SendEmailRequestDTO(
            to=decrypted_user_data.email,
            subject="Email Verification",
            template_name="sign_up_email.html",
            html_substitutions={
                "verification_url": f"http://cozi-api.localhost/manager/auth/verify?d={encrypted_data.data}",
                "user_name": decrypted_user_data.first_name,
            },
        ).model_dump()
    )

    # GENERATE UNIQUE ID

    manager_id = generate_user_id()

    # INSERT INTO MANAGER TABLE

    session.add(
        new_manager := Admin(
            id=manager_id,
            email_address=decrypted_user_data.email,
            first_name=decrypted_user_data.first_name,
            last_name=decrypted_user_data.last_name,
            hashed_password=bcrypt.hashpw(decrypted_user_data.password.encode("utf-8"), bcrypt.gensalt()),
            phone_number=decrypted_user_data.phone,
        )
    )

    # INSERT INTO MANAGER VERIFICATION TABLE

    session.add(
        ManagerVerification(
            manager_id=new_manager.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
        )
    )

    session.commit()

    return
