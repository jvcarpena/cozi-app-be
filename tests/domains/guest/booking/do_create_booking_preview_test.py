from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage

path = f"/test/api/v1/guest/bookings/preview"


def test_do_create_booking_preview(client, container_engine, guest, resort):

    request = HTTPRequestHelper(
        body={
            "resort_id": resort.id,
            "check_in": str(datetime.now(tz=ZoneInfo("Asia/Manila"))),
            "check_out": str(datetime.now(tz=ZoneInfo("Asia/Manila")) + timedelta(days=1)),
            "num_guests": 24,
        }
    ).create_request(guest)

    response = client.post(path, headers=request.headers, json=request.body)
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["resort_name"] == resort.name


def test_do_create_booking_preview_invalid_check_in(client, container_engine, guest, resort):

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


def test_do_create_booking_preview_invalid_num_guests(client, container_engine, guest, resort):

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
