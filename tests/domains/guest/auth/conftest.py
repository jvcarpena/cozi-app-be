from datetime import datetime, timezone, timedelta

import bcrypt
import pytest

from core.models.guest import Guest
from core.models.guest_password_reset_request import GuestPasswordResetRequest
from core.models.guest_verification import GuestVerification


def _create_password_reset_request(db_session, guest, expires_at, consumed_at=None):
    db_session.add(
        reset_request := GuestPasswordResetRequest(
            guest_id=guest.id,
            expires_at=expires_at,
            request_consumed_at=consumed_at,
        )
    )

    db_session.commit()

    return reset_request


@pytest.fixture
def password_reset_request(db_session, guest):
    """
    An active request: not expired and not consumed.
    """

    yield _create_password_reset_request(db_session, guest, datetime.now(tz=timezone.utc) + timedelta(hours=1))


@pytest.fixture
def expired_password_reset_request(db_session, guest):

    yield _create_password_reset_request(db_session, guest, datetime.now(tz=timezone.utc) - timedelta(minutes=1))


@pytest.fixture
def consumed_password_reset_request(db_session, guest):

    yield _create_password_reset_request(
        db_session,
        guest,
        datetime.now(tz=timezone.utc) + timedelta(hours=1),
        consumed_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def unverified_guest(db_session):
    db_session.add(
        unverified_guest := Guest(
            id="unverified_guest",
            email_address="unverified_guest@gmail.com",
            hashed_password=bcrypt.hashpw("unverified1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="unverified",
            last_name="guest",
        )
    )

    db_session.add(
        GuestVerification(
            guest_id=unverified_guest.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()
    yield unverified_guest


@pytest.fixture
def unverified_guest_expired_link(db_session):
    db_session.add(
        unverified_guest_expired_link := Guest(
            id="unverified_guest_expired_link",
            email_address="unverified_guest_expired_link@gmail.com",
            hashed_password=bcrypt.hashpw("linkexpired1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="unverified guest",
            last_name="link expired",
        )
    )

    db_session.add(
        GuestVerification(
            guest_id=unverified_guest_expired_link.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
        )
    )

    db_session.commit()
    yield unverified_guest_expired_link
