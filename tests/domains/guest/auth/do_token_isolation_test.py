import pytest

from datetime import datetime, timezone

from core.models.admin import Admin
from core.models.master import Master
from core.models.organization import Organization
from core.services.http_request_helper import HTTPRequestHelper


@pytest.fixture
def admin(db_session):
    db_session.add(admin := Admin(id="admin", email_address="admin@gmail.com"))

    db_session.commit()

    yield admin


def test_admin_token_rejected_on_guest_booking_history(client, admin):
    """
    Tokens issued to the manager (admin) domain must not work on guest endpoints.
    """

    request = HTTPRequestHelper(query_string_parameters={"status": "PENDING"}).create_request(admin)

    response = client.get(
        "/test/api/v1/guest/bookings", headers=request.headers, params=request.query_string_parameters
    )

    assert response.status_code == 401


def test_admin_token_rejected_on_guest_resort_review(client, admin, resort):
    request = HTTPRequestHelper(
        body={
            "resort_id": resort.id,
            "overall_rating": 4,
            "cleanliness_rating": 4,
            "value_rating": 4,
            "comment": "TEST_COMMENT",
        }
    ).create_request(admin)

    response = client.post(
        f"/test/api/v1/guest/resorts/{resort.id}/reviews", headers=request.headers, json=request.body
    )

    assert response.status_code == 401


def test_master_token_rejected_on_guest_booking_history(client, db_session):

    db_session.add(
        master := Master(
            id="master", email_address="master@gmail.com", organization=Organization(name="TEST_ORGANIZATION")
        )
    )

    db_session.commit()

    request = HTTPRequestHelper(query_string_parameters={"status": "PENDING"}).create_request(master)

    response = client.get(
        "/test/api/v1/guest/bookings", headers=request.headers, params=request.query_string_parameters
    )

    assert response.status_code == 401


def test_removed_user_token_rejected(client, db_session, guest):
    """
    A removed user is refused even though their token has not expired yet.
    """

    guest.deleted_at = datetime.now(tz=timezone.utc)

    db_session.commit()

    request = HTTPRequestHelper(query_string_parameters={"status": "PENDING"}).create_request(guest)

    response = client.get(
        "/test/api/v1/guest/bookings", headers=request.headers, params=request.query_string_parameters
    )

    assert response.status_code == 401
