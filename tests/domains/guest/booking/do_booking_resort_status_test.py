from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.booking import Booking
from core.models.resort import ResortStatusEnum
from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage

# ONLY AN ACTIVE RESORT CAN BE BOOKED. A DRAFT (INACTIVE) AND A RESORT UNDER MAINTENANCE ARE CLOSED TO NEW BOOKINGS.

path = "/test/api/v1/guest/bookings"

NOT_BOOKABLE_STATUSES = [ResortStatusEnum.INACTIVE, ResortStatusEnum.MAINTENANCE]


def booking_body(resort) -> dict:

    return {
        "resort_id": resort.id,
        "check_in": str(datetime.now(ZoneInfo("Asia/Manila"))),
        "check_out": str(datetime.now(ZoneInfo("Asia/Manila")) + timedelta(days=1)),
        "num_guests": 2,
    }


def set_status(db_session, resort, status: ResortStatusEnum):

    resort.status = status

    db_session.commit()


@pytest.mark.parametrize("status", NOT_BOOKABLE_STATUSES)
def test_create_booking_resort_is_not_open(client, container_engine, db_session, resort, guest, status):

    set_status(db_session, resort, status)

    request = HTTPRequestHelper(body=booking_body(resort)).create_request(guest)

    response = client.post(path, headers=request.headers, json=request.body)

    assert response.status_code == 400
    assert response.json()["detail"] == GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name

    with Session(container_engine) as session:
        assert session.scalars(select(Booking)).all() == []


@pytest.mark.parametrize("status", NOT_BOOKABLE_STATUSES)
def test_booking_preview_resort_is_not_open(client, db_session, resort, guest, status):

    set_status(db_session, resort, status)

    request = HTTPRequestHelper(body=booking_body(resort)).create_request(guest)

    response = client.post(f"{path}/preview", headers=request.headers, json=request.body)

    assert response.status_code == 400
    assert response.json()["detail"] == GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name


def test_create_booking_resort_is_open_again_after_it_is_activated(client, db_session, resort, guest):
    """
    A manager closes a resort and later reopens it: bookings work again.
    """

    set_status(db_session, resort, ResortStatusEnum.MAINTENANCE)

    request = HTTPRequestHelper(body=booking_body(resort)).create_request(guest)

    assert client.post(path, headers=request.headers, json=request.body).status_code == 400

    set_status(db_session, resort, ResortStatusEnum.ACTIVE)

    assert client.post(path, headers=request.headers, json=request.body).status_code == 200
