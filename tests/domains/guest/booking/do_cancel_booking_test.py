from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from core.models.booking import Booking
from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage


def test_cancel_booking(client, container_engine, booking, guest):

    path = f"/test/api/v1/guest/bookings/{booking.id}/cancel"

    request = HTTPRequestHelper(
        body={"reason": "CANCEL THIS BOOKING"},
    ).create_request(guest)

    response = client.put(path, headers=request.headers, json=request.body)

    assert response.status_code == 200

    with Session(container_engine) as session:
        booking = session.scalars(
            select(Booking).where(
                and_(
                    Booking.id == booking.id,
                    Booking.guest_id == guest.id,
                )
            )
        ).one()

        assert booking.cancelled_at is not None
        assert booking.cancel_reason == "CANCEL THIS BOOKING"


def test_cancel_booking_not_exist(client, db_session, guest):

    path = "/test/api/v1/guest/bookings/67/cancel"

    request = HTTPRequestHelper(
        body={"reason": "BOOKING NOT EXIST"},
    ).create_request(guest)

    response = client.put(path, headers=request.headers, json=request.body)

    response_body = response.json()

    assert response.status_code == 404
    assert response_body["detail"] == GuestErrorMessage.BOOKING_DOES_NOT_EXIST.name
