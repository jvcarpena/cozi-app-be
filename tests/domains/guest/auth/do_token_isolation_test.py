import pytest

from core.models.admin import Admin
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
