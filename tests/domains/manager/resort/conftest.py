from datetime import datetime, timezone, timedelta
from decimal import Decimal

import bcrypt
import pytest

from core.models.admin import Admin
from core.models.booking import Booking, BookingStatusEnum
from core.models.manager_verification import ManagerVerification
from core.models.master import Master
from core.models.organization import Organization
from core.models.resort import Resort, ResortStatusEnum

# THESE FIXTURES BUILD TWO SEPARATE BUSINESSES, SO THE TESTS CAN PROVE A MANAGER NEVER REACHES THE OTHER ONE:
#
#   master  -> ORGANIZATION A -> master_resort (ACTIVE, managed by resort_admin) and master_draft_resort (INACTIVE)
#   other_master -> ORGANIZATION B -> other_resort (ACTIVE, managed by other_admin)


def create_master(db_session, user_id: str, email: str, organization_name: str) -> Master:

    db_session.add(
        master := Master(
            id=user_id,
            email_address=email,
            hashed_password=bcrypt.hashpw("master1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="verified",
            last_name="master",
            organization=Organization(name=organization_name),
        )
    )

    db_session.add(
        ManagerVerification(
            manager_id=master.id,
            latest_email_sent_at=datetime.now(tz=timezone.utc),
            verified_at=datetime.now(tz=timezone.utc),
        )
    )

    db_session.commit()

    return master


def create_resort(db_session, organization_id: int, name: str, status=ResortStatusEnum.ACTIVE) -> Resort:

    db_session.add(
        resort := Resort(
            organization_id=organization_id,
            name=name,
            status=status,
            description=f"{name} DESCRIPTION",
            base_price_per_night=Decimal("25000"),
            base_price_per_day_use=Decimal("12000"),
            currency="PHP",
            max_guests=25,
            num_bedrooms=4,
            num_bathrooms=5,
            address=f"{name} ADDRESS",
        )
    )

    db_session.commit()

    return resort


def create_admin(db_session, user_id: str, email: str, resort_id: int | None, deleted_at=None) -> Admin:

    db_session.add(
        admin := Admin(
            id=user_id,
            email_address=email,
            hashed_password=bcrypt.hashpw("admin1234".encode("utf-8"), bcrypt.gensalt()),
            first_name="verified",
            last_name="admin",
            resort_id=resort_id,
            deleted_at=deleted_at,
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

    return admin


@pytest.fixture
def master(db_session):

    yield create_master(db_session, "master", "master@gmail.com", "ORGANIZATION_A")


@pytest.fixture
def other_master(db_session):

    yield create_master(db_session, "other_master", "other_master@gmail.com", "ORGANIZATION_B")


@pytest.fixture
def master_resort(db_session, master):

    yield create_resort(db_session, master.organization_id, "MASTER_RESORT")


@pytest.fixture
def master_draft_resort(db_session, master, master_resort):
    """
    A second resort of the same master, still a draft. It depends on master_resort so it is created after it.
    """

    yield create_resort(db_session, master.organization_id, "MASTER_DRAFT_RESORT", ResortStatusEnum.INACTIVE)


@pytest.fixture
def other_resort(db_session, other_master):

    yield create_resort(db_session, other_master.organization_id, "OTHER_RESORT")


@pytest.fixture
def resort_admin(db_session, master_resort):
    """
    The admin of master_resort.
    """

    yield create_admin(db_session, "resort_admin", "resort_admin@gmail.com", master_resort.id)


@pytest.fixture
def other_admin(db_session, other_resort):
    """
    The admin of other_resort, a resort of a different master.
    """

    yield create_admin(db_session, "other_admin", "other_admin@gmail.com", other_resort.id)


@pytest.fixture
def removed_admin(db_session, master_resort):
    """
    An admin that was removed from master_resort but still holds a token that has not expired.
    """

    yield create_admin(
        db_session,
        "removed_admin",
        "removed_admin@gmail.com",
        master_resort.id,
        deleted_at=datetime.now(tz=timezone.utc),
    )


@pytest.fixture
def create_booking(db_session, guest):
    """
    Returns a function that books a resort for the guest. By default it is a PENDING booking that ends in 3 days.
    """

    def _create_booking(
        resort: Resort,
        status: BookingStatusEnum = BookingStatusEnum.PENDING,
        check_out_in: timedelta = timedelta(days=3),
    ) -> Booking:

        db_session.add(
            booking := Booking(
                guest_id=guest.id,
                resort_id=resort.id,
                status=status,
                check_in=datetime.now(tz=timezone.utc) + check_out_in - timedelta(days=2),
                check_out=datetime.now(tz=timezone.utc) + check_out_in,
                num_guests=2,
                nights=2,
                total_price=Decimal("50000"),
                currency="PHP",
            )
        )

        db_session.commit()

        return booking

    return _create_booking
