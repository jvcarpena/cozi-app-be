from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.booking import Booking, BookingStatusEnum
from core.models.resort_availability import ResortAvailability, ResortAvailabilityStatus
from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage

path = "/test/api/v1/guest/bookings"

MANILA = ZoneInfo("Asia/Manila")


def booking_body(resort, check_in: datetime, check_out: datetime) -> dict:

    return {
        "resort_id": resort.id,
        "check_in": check_in.isoformat(),
        "check_out": check_out.isoformat(),
        "num_guests": 2,
    }


def create_booking(client, guest, resort, check_in: datetime, check_out: datetime):

    request = HTTPRequestHelper(body=booking_body(resort, check_in, check_out)).create_request(guest)

    return client.post(path, headers=request.headers, json=request.body)


def get_availabilities(container_engine, resort_id: int) -> list[ResortAvailability]:

    with Session(container_engine) as session:
        return list(
            session.scalars(
                select(ResortAvailability)
                .where(ResortAvailability.resort_id == resort_id)
                .order_by(ResortAvailability.date)
            ).all()
        )


# TWO NIGHTS: THE GUESTS STAY ON THE 10TH AND 11TH AND LEAVE ON THE 12TH.

CHECK_IN = datetime(2030, 1, 10, 14, 0, tzinfo=MANILA)
CHECK_OUT = datetime(2030, 1, 12, 12, 0, tzinfo=MANILA)


def test_create_booking_blocks_the_booked_dates(client, container_engine, guest, resort):

    response = create_booking(client, guest, resort, CHECK_IN, CHECK_OUT)

    assert response.status_code == 200

    availabilities = get_availabilities(container_engine, resort.id)

    assert [availability.date for availability in availabilities] == [date(2030, 1, 10), date(2030, 1, 11)]
    assert {availability.status for availability in availabilities} == {ResortAvailabilityStatus.BOOKED}
    assert {availability.booking_id for availability in availabilities} == {response.json()["id"]}


def test_create_booking_dates_already_taken(client, container_engine, guest, resort):

    create_booking(client, guest, resort, CHECK_IN, CHECK_OUT)

    # OVERLAPS THE NIGHT OF THE 11TH

    response = create_booking(
        client, guest, resort, datetime(2030, 1, 11, 14, 0, tzinfo=MANILA), datetime(2030, 1, 13, 12, 0, tzinfo=MANILA)
    )

    assert response.status_code == 400
    assert response.json()["detail"] == GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name

    # THE REJECTED BOOKING LEFT NOTHING BEHIND

    assert len(get_availabilities(container_engine, resort.id)) == 2


def test_create_booking_starts_the_day_the_previous_guests_leave(client, guest, resort):

    create_booking(client, guest, resort, CHECK_IN, CHECK_OUT)

    response = create_booking(
        client, guest, resort, datetime(2030, 1, 12, 14, 0, tzinfo=MANILA), datetime(2030, 1, 13, 12, 0, tzinfo=MANILA)
    )

    assert response.status_code == 200


def test_create_day_use_booking_blocks_that_date(client, container_engine, guest, resort):

    check_in = datetime(2030, 2, 1, 9, 0, tzinfo=MANILA)
    check_out = datetime(2030, 2, 1, 17, 0, tzinfo=MANILA)

    response = create_booking(client, guest, resort, check_in, check_out)

    assert response.status_code == 200
    assert response.json()["booking_type"] == "day_use"
    assert [availability.date for availability in get_availabilities(container_engine, resort.id)] == [date(2030, 2, 1)]

    second_response = create_booking(client, guest, resort, check_in, check_out)

    assert second_response.status_code == 400
    assert second_response.json()["detail"] == GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name


def test_preview_booking_dates_already_taken(client, guest, resort):

    create_booking(client, guest, resort, CHECK_IN, CHECK_OUT)

    request = HTTPRequestHelper(body=booking_body(resort, CHECK_IN, CHECK_OUT)).create_request(guest)

    response = client.post(f"{path}/preview", headers=request.headers, json=request.body)

    assert response.status_code == 400
    assert response.json()["detail"] == GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name


def test_cancel_booking_frees_the_dates(client, container_engine, guest, resort):

    booking_id = create_booking(client, guest, resort, CHECK_IN, CHECK_OUT).json()["id"]

    request = HTTPRequestHelper(body={"reason": "CHANGE OF PLANS"}).create_request(guest)

    response = client.put(f"{path}/{booking_id}/cancel", headers=request.headers, json=request.body)

    assert response.status_code == 200

    with Session(container_engine) as session:
        booking = session.get(Booking, booking_id)

        assert booking.status == BookingStatusEnum.CANCELLED
        assert booking.cancelled_at is not None
        assert booking.cancel_reason == "CHANGE OF PLANS"

    assert get_availabilities(container_engine, resort.id) == []

    # THE SAME DATES CAN BE BOOKED AGAIN

    assert create_booking(client, guest, resort, CHECK_IN, CHECK_OUT).status_code == 200


def test_cancel_booking_twice_changes_nothing(client, container_engine, guest, resort):

    booking_id = create_booking(client, guest, resort, CHECK_IN, CHECK_OUT).json()["id"]

    first_request = HTTPRequestHelper(body={"reason": "FIRST"}).create_request(guest)
    second_request = HTTPRequestHelper(body={"reason": "SECOND"}).create_request(guest)

    client.put(f"{path}/{booking_id}/cancel", headers=first_request.headers, json=first_request.body)
    response = client.put(f"{path}/{booking_id}/cancel", headers=second_request.headers, json=second_request.body)

    assert response.status_code == 200

    with Session(container_engine) as session:
        assert session.get(Booking, booking_id).cancel_reason == "FIRST"
