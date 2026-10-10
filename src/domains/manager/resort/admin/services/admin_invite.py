import os
from datetime import datetime, timezone, timedelta

from sqlalchemy import update, and_
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerLinkPurpose, ManagerPasswordResetRequest
from core.models.master import Master
from core.models.resort import Resort
from core.services.password_reset_token_handler import MANAGER_PURPOSE, PasswordResetTokenHandler
from core.services.send_email import SendEmailRequestDTO
from core.tools.celery.tasks.email_task import send_email_task

API_BASE_URL = os.environ.get("API_BASE_URL", "http://cozi-api.localhost")

# AN INVITE HAS TO SURVIVE THE ADMIN NOT CHECKING THEIR EMAIL FOR A WHILE, A PASSWORD RESET LINK DOES NOT (1 HOUR).
ADMIN_INVITE_EXPIRY = timedelta(days=7)

# HOW LONG THE MASTER HAS TO WAIT BEFORE THE INVITE CAN BE SENT AGAIN, SO AN INBOX CANNOT BE FLOODED.
ADMIN_INVITE_RESEND_COOLDOWN = timedelta(minutes=5)


def close_open_invites(session: Session, admin_id: str):
    """
    Marks every link of the admin that was not used yet as used, so an older link stops working.
    """

    session.execute(
        update(ManagerPasswordResetRequest)
        .where(
            and_(
                ManagerPasswordResetRequest.manager_id == admin_id,
                ManagerPasswordResetRequest.request_consumed_at.is_(None),
            )
        )
        .values(request_consumed_at=datetime.now(tz=timezone.utc))
    )


def add_invite_request(session: Session, admin: Admin) -> ManagerPasswordResetRequest:
    """
    Adds the link request of an invite. The admin must already exist in the database (flush first),
    because nothing tells SQLAlchemy that the request has to be inserted after the admin.
    """

    session.add(
        invite_request := ManagerPasswordResetRequest(
            manager_id=admin.id,
            purpose=ManagerLinkPurpose.INVITE,
            expires_at=datetime.now(tz=timezone.utc) + ADMIN_INVITE_EXPIRY,
        )
    )

    session.flush()

    return invite_request


def send_admin_invite_email(master: Master, resort: Resort, admin: Admin, invite_request: ManagerPasswordResetRequest):
    """
    Queues the invite email. The link opens the same page as a password reset, with a token that is signed for managers.
    """

    token = PasswordResetTokenHandler(
        request_id=invite_request.id, expiry_date=invite_request.expires_at, purpose=MANAGER_PURPOSE
    ).generate_reset_token()

    send_email_task.delay(
        SendEmailRequestDTO(
            to=admin.email_address,
            subject=f"You have been invited to manage {resort.name}",
            template_name="admin_invite_email.html",
            html_substitutions={
                "user_name": admin.first_name,
                "inviter_name": f"{master.first_name} {master.last_name}".strip(),
                "resort_name": resort.name,
                "invite_url": f"{API_BASE_URL}/manager/auth/reset-password?d={token}",
                "expires_in_days": ADMIN_INVITE_EXPIRY.days,
            },
        ).model_dump()
    )
