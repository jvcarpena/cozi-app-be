import os
from datetime import datetime, timezone, timedelta

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models.manager_verification import ManagerVerification
from core.models.master import Master
from core.models.organization import Organization
from core.services.secure_payload_handler import SecurePayloadHandler
from core.services.send_email import SendEmailRequestDTO
from core.services.user_id_generator import generate_user_id
from core.tools.celery.tasks.email_task import send_email_task
from domains.guest.dtos.sign_up_login_dto import EncryptedDataDTO, validate_password_length
from domains.manager.auth.get_manager_by_email import get_manager_by_email
from domains.manager.dtos.sign_up_dto import DecryptedManagerSignUpDataDTO
from domains.manager.enums import ManagerErrorMessage

QUEUE_NAME = os.environ.get("EMAIL_NOTIF_QUEUE", "email_notif_queue_develop")


def sign_up(encrypted_data: EncryptedDataDTO, session: Session):
    """
    Everyone who signs up as a manager becomes a master, whether they own one resort or many. Admins are never
    created here: a master invites them to a resort.
    """

    # DECRYPT DATA

    decrypted_user_data: DecryptedManagerSignUpDataDTO = SecurePayloadHandler(
        data_to_decrypt=encrypted_data.data
    ).decrypt_payload(is_manager_sign_up=True)

    # CHECK THE PASSWORD LENGTH

    validate_password_length(decrypted_user_data.password)

    # GET EXISTING MANAGER FROM THE DB. AN EMAIL CANNOT BE BOTH A MASTER AND AN ADMIN, SO LOOK AT BOTH TYPES.

    existing_user = get_manager_by_email(session, decrypted_user_data.email)

    # CHECK IF THE MANAGER IS ALREADY VERIFIED

    if existing_user:

        # AN EMAIL THAT BELONGS TO AN ADMIN (INVITED BY A MASTER) CANNOT BE USED TO SIGN UP.
        # IF VERIFIED, RAISE EMAIL REGISTERED ERROR
        if not isinstance(existing_user, Master) or existing_user.verification.verified_at:

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

                existing_user.organization.name = decrypted_user_data.organization_name

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

    # INSERT INTO ORGANIZATION, MASTER AND MANAGER VERIFICATION TABLES IN ONE TRANSACTION.
    # THE ORGANIZATION IS THE BUSINESS THAT OWNS THE RESORTS OF THE MASTER.

    new_master = Master(
        id=generate_user_id(),
        email_address=decrypted_user_data.email,
        first_name=decrypted_user_data.first_name,
        last_name=decrypted_user_data.last_name,
        hashed_password=bcrypt.hashpw(decrypted_user_data.password.encode("utf-8"), bcrypt.gensalt()),
        phone_number=decrypted_user_data.phone,
        organization=Organization(name=decrypted_user_data.organization_name),
    )

    new_master.verification = ManagerVerification(
        manager_id=new_master.id,
        latest_email_sent_at=datetime.now(tz=timezone.utc),
    )

    session.add(new_master)

    session.commit()

    return
