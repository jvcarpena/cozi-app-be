from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from core.models.booking import Booking
from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage

path = "/test/api/v1/guest/bookings"


def test_do_create_booking(client, container_engine, resort, guest):

    request = HTTPRequestHelper(
        body={
            "resort_id": resort.id,
            "check_in": str(datetime.now(ZoneInfo("Asia/Manila"))),
            "check_out": str(datetime.now(ZoneInfo("Asia/Manila")) + timedelta(days=1)),
            "num_guests": 24,
            "special_request": "BBQ grill",
        }
    ).create_request(guest)

    response = client.post(path, headers=request.headers, json=request.body)
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["resort_name"] == resort.name

    with Session(container_engine) as session:
        booking = session.scalars(
            select(Booking).where(
                and_(
                    Booking.guest_id == guest.id,
                    Booking.resort_id == resort.id,
                )
            )
        ).one()

        assert booking is not None
        assert booking.special_request == "BBQ grill"


def test_do_create_booking_invalid_check_in(client, guest, resort):

    request = HTTPRequestHelper(
        body={
            "resort_id": resort.id,
            "check_in": str(datetime.now(tz=ZoneInfo("Asia/Manila")) + timedelta(days=1)),
            "check_out": str(datetime.now(tz=ZoneInfo("Asia/Manila"))),
            "num_guests": 24,
        }
    ).create_request(guest)

    response = client.post(path, headers=request.headers, json=request.body)
    response_body = response.json()

    assert response.status_code == 422
    assert response_body["detail"] == GuestErrorMessage.CHECKOUT_MUST_BE_AFTER_CHECK_IN.name


def test_do_create_booking_invalid_num_guests(client, guest, resort):

    request = HTTPRequestHelper(
        body={
            "resort_id": resort.id,
            "check_in": str(datetime.now(tz=ZoneInfo("Asia/Manila"))),
            "check_out": str(datetime.now(tz=ZoneInfo("Asia/Manila")) + timedelta(days=1)),
            "num_guests": 0,
        }
    ).create_request(guest)

    response = client.post(path, headers=request.headers, json=request.body)
    response_body = response.json()

    assert response.status_code == 422
    assert response_body["detail"] == GuestErrorMessage.NUM_GUEST_MUST_BE_AT_LEAST_1.name
