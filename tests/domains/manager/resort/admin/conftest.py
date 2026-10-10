from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

import pytest

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerLinkPurpose, ManagerPasswordResetRequest
from core.models.manager_verification import ManagerVerification
from core.services.password_reset_token_handler import MANAGER_PURPOSE, PasswordResetTokenHandler
from tests.domains.manager.resort.helpers import BASE_PATH


def admin_path(resort, suffix: str = "") -> str:

    return f"{BASE_PATH}/{resort.id}/admin{suffix}"


def invite_payload(**overrides) -> dict:
    """
    A valid invite payload. Pass a field to replace it, or set a field to None to leave it out.
    """

    payload = {
        "email": "new_admin@gmail.com",
        "first_name": "Maria",
        "last_name": "Santos",
        "phone": "09171234567",
    }

    payload.update(overrides)

    return {key: value for key, value in payload.items() if value is not None}


def token_in_email(email_request: dict) -> str:
    """
    The token inside the link of the email that was queued.
    """

    return parse_qs(urlparse(email_request["html_substitutions"]["invite_url"]).query)["d"][0]


def build_token(request: ManagerPasswordResetRequest) -> str:

    return PasswordResetTokenHandler(
        request_id=request.id, expiry_date=request.expires_at, purpose=MANAGER_PURPOSE
    ).generate_reset_token()


@pytest.fixture
def send_email_task_mock(mocker):
    """
    Replaces the Celery task so no broker, worker or SMTP server is needed. The test only checks what was queued.
    """

    return mocker.patch("domains.manager.resort.admin.services.admin_invite.send_email_task")


def create_pending_admin(db_session, resort, invite_sent_minutes_ago: int) -> Admin:
    """
    An admin a master invited who has not opened the link yet: no password, not verified, one open invite link.
    """

    sent_at = datetime.now(tz=timezone.utc) - timedelta(minutes=invite_sent_minutes_ago)

    db_session.add(
        admin := Admin(
            id="pending_admin",
            email_address="pending_admin@gmail.com",
            first_name="pending",
            last_name="admin",
            resort_id=resort.id,
        )
    )

    db_session.add(ManagerVerification(manager_id=admin.id, latest_email_sent_at=sent_at))

    db_session.flush()

    db_session.add(
        ManagerPasswordResetRequest(
            manager_id=admin.id,
            purpose=ManagerLinkPurpose.INVITE,
            expires_at=sent_at + timedelta(days=7),
        )
    )

    db_session.commit()

    return admin


@pytest.fixture
def pending_admin(db_session, master_resort):
    """
    Invited 10 minutes ago, so the invite can be sent again.
    """

    yield create_pending_admin(db_session, master_resort, invite_sent_minutes_ago=10)


@pytest.fixture
def recently_invited_admin(db_session, master_resort):
    """
    Invited 1 minute ago, still inside the cooldown.
    """

    yield create_pending_admin(db_session, master_resort, invite_sent_minutes_ago=1)
