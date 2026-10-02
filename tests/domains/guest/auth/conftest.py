from datetime import datetime, timezone, timedelta

import bcrypt
import pytest

from core.models.guest import Guest
from core.models.guest_verification import GuestVerification


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
