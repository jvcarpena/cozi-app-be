from datetime import datetime, timezone, timedelta

import bcrypt
import pytest

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from core.models.manager_verification import ManagerVerification
from core.models.master import Master
from core.models.organization import Organization


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


def _create_master(db_session, user_id, email, password, first_name, last_name, latest_email_sent_at, verified_at):
    """
    Creates a master with its own organization and a verification row, like the manager sign up does.
    """

    db_session.add(
        master := Master(
            id=user_id,
            email_address=email,
            hashed_password=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()),
            first_name=first_name,
            last_name=last_name,
            organization=Organization(name=f"{user_id.upper()}_ORGANIZATION"),
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=master.id,
            latest_email_sent_at=latest_email_sent_at,
            verified_at=verified_at,
        )
    )

    db_session.commit()

    return master


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
    """
    A verified master. Every manager sign up creates a master, so this is the default manager of the tests.
    """

    yield _create_master(
        db_session,
        "manager",
        "manager@gmail.com",
        "manager1234",
        "verified",
        "manager",
        latest_email_sent_at=datetime.now(tz=timezone.utc),
        verified_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def unverified_manager(db_session):

    yield _create_master(
        db_session,
        "unverified_manager",
        "unverified_manager@gmail.com",
        "unverified1234",
        "unverified",
        "manager",
        latest_email_sent_at=datetime.now(tz=timezone.utc),
        verified_at=None,
    )


@pytest.fixture
def unverified_manager_expired_link(db_session):

    yield _create_master(
        db_session,
        "unverified_manager_expired_link",
        "unverified_manager_expired_link@gmail.com",
        "linkexpired1234",
        "unverified manager",
        "link expired",
        latest_email_sent_at=datetime.now(tz=timezone.utc) - timedelta(hours=25),
        verified_at=None,
    )


@pytest.fixture
def admin(db_session, resort):
    """
    A verified admin that manages the `resort` fixture.
    """

    db_session.add(
        admin := Admin(
            id="admin",
            email_address="admin@gmail.com",
            hashed_password=bcrypt.hashpw("admin1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="verified",
            last_name="admin",
            resort_id=resort.id,
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=admin.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
            verified_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()

    yield admin


@pytest.fixture
def invited_admin(db_session, resort):
    """
    An admin a master invited who has not opened the link yet: no password and not verified.
    """

    db_session.add(
        invited_admin := Admin(
            id="invited_admin",
            email_address="invited_admin@gmail.com",
            first_name="invited",
            last_name="admin",
            resort_id=resort.id,
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=invited_admin.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()

    yield invited_admin


@pytest.fixture
def deleted_admin(db_session):
    """
    A removed admin. The email is kept on purpose, so the tests show that a removed admin is refused even if the
    email was not cleared.
    """

    db_session.add(
        deleted_admin := Admin(
            id="deleted_admin",
            email_address="deleted_admin@gmail.com",
            hashed_password=bcrypt.hashpw("deleted1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="DELETED",
            last_name="ADMIN",
            deleted_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=deleted_admin.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
            verified_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()

    yield deleted_admin
