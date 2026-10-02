from datetime import datetime, timezone, timedelta

import bcrypt
import pytest

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from core.models.manager_verification import ManagerVerification


def _create_password_reset_request(db_session, manager, expires_at, consumed_at=None):
    db_session.add(
        reset_request := ManagerPasswordResetRequest(
            manager_id=manager.id,
            expires_at=expires_at,
            request_consumed_at=consumed_at,
        )
    )

    db_session.commit()

    return reset_request


@pytest.fixture
def password_reset_request(db_session, manager):
    """
    An active request: not expired and not consumed.
    """

    yield _create_password_reset_request(db_session, manager, datetime.now(tz=timezone.utc) + timedelta(hours=1))


@pytest.fixture
def expired_password_reset_request(db_session, manager):

    yield _create_password_reset_request(db_session, manager, datetime.now(tz=timezone.utc) - timedelta(minutes=1))


@pytest.fixture
def consumed_password_reset_request(db_session, manager):

    yield _create_password_reset_request(
        db_session,
        manager,
        datetime.now(tz=timezone.utc) + timedelta(hours=1),
        consumed_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def manager(db_session):
    db_session.add(
        manager := Admin(
            id="manager",
            email_address="manager@gmail.com",
            hashed_password=bcrypt.hashpw("manager1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="verified",
            last_name="manager",
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=manager.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
            verified_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()
    yield manager


@pytest.fixture
def unverified_manager(db_session):
    db_session.add(
        unverified_manager := Admin(
            id="unverified_manager",
            email_address="unverified_manager@gmail.com",
            hashed_password=bcrypt.hashpw("unverified1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="unverified",
            last_name="manager",
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=unverified_manager.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()
    yield unverified_manager


@pytest.fixture
def unverified_manager_expired_link(db_session):
    db_session.add(
        unverified_manager_expired_link := Admin(
            id="unverified_manager_expired_link",
            email_address="unverified_manager_expired_link@gmail.com",
            hashed_password=bcrypt.hashpw("linkexpired1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="unverified manager",
            last_name="link expired",
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=unverified_manager_expired_link.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
        )
    )

    db_session.commit()
    yield unverified_manager_expired_link
