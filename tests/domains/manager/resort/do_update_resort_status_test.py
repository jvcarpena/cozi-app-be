from datetime import timedelta

import pytest
from sqlalchemy.orm import Session

from core.models.booking import BookingStatusEnum
from core.models.resort import Resort, ResortStatusEnum
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.resort.helpers import BASE_PATH, call

CLOSED_STATUSES = [ResortStatusEnum.INACTIVE, ResortStatusEnum.MAINTENANCE]


def get_status(container_engine, resort_id: int) -> str:

    with Session(container_engine) as session:
        return session.get(Resort, resort_id).status


def set_status(client, user, resort, status) -> object:

    return call(client, "PUT", f"{BASE_PATH}/{resort.id}/status", user, {"status": status})


def test_update_resort_status_activate_a_draft(client, container_engine, master, master_draft_resort):

    response = set_status(client, master, master_draft_resort, "ACTIVE")

    assert response.status_code == 200

    # THE RESPONSE IS THE UPDATED RESORT

    assert response.json()["resort"]["id"] == master_draft_resort.id
    assert response.json()["resort"]["status"] == ResortStatusEnum.ACTIVE

    assert get_status(container_engine, master_draft_resort.id) == ResortStatusEnum.ACTIVE


def test_update_resort_status_activated_resort_appears_for_guests(client, master, master_draft_resort):
    guest_list = "/test/api/v1/guest/resorts"

    assert master_draft_resort.id not in [resort["id"] for resort in client.get(guest_list).json()["resorts"]]

    set_status(client, master, master_draft_resort, "ACTIVE")

    assert master_draft_resort.id in [resort["id"] for resort in client.get(guest_list).json()["resorts"]]


def test_update_resort_status_admin_can_change_the_status_of_their_resort(
    client, container_engine, master_resort, resort_admin
):

    response = set_status(client, resort_admin, master_resort, "MAINTENANCE")

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.MAINTENANCE


@pytest.mark.parametrize("status", list(ResortStatusEnum))
def test_update_resort_status_every_status_can_be_set(client, container_engine, master, master_resort, status):

    response = set_status(client, master, master_resort, status)

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == status


def test_update_resort_status_same_status_is_fine(client, master, master_resort, create_booking):
    """
    Setting ACTIVE on an ACTIVE resort changes nothing, so upcoming bookings are no reason to refuse it.
    """

    create_booking(master_resort)

    response = set_status(client, master, master_resort, "ACTIVE")

    assert response.status_code == 200


# CLOSING A LIVE RESORT IS BLOCKED WHILE GUESTS STILL HAVE BOOKINGS AT IT


@pytest.mark.parametrize("new_status", CLOSED_STATUSES)
@pytest.mark.parametrize("booking_status", [BookingStatusEnum.PENDING, BookingStatusEnum.CONFIRMED])
def test_update_resort_status_blocked_by_upcoming_booking(
    client, container_engine, master, master_resort, create_booking, new_status, booking_status
):
    create_booking(master_resort, booking_status)

    response = set_status(client, master, master_resort, new_status)

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_HAS_UPCOMING_BOOKINGS.name
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


def test_update_resort_status_admin_is_blocked_too(
    client, container_engine, master_resort, resort_admin, create_booking
):
    create_booking(master_resort)

    response = set_status(client, resort_admin, master_resort, "INACTIVE")

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_HAS_UPCOMING_BOOKINGS.name
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


def test_update_resort_status_blocked_when_the_booking_ends_later_today(client, master, master_resort, create_booking):
    create_booking(master_resort, check_out_in=timedelta(hours=1))

    response = set_status(client, master, master_resort, "INACTIVE")

    assert response.status_code == 400


def test_update_resort_status_one_upcoming_booking_among_finished_ones_still_blocks(
    client, master, master_resort, create_booking
):
    create_booking(master_resort, BookingStatusEnum.CANCELLED)
    create_booking(master_resort, BookingStatusEnum.COMPLETED, check_out_in=timedelta(days=-5))
    create_booking(master_resort, BookingStatusEnum.CONFIRMED)

    response = set_status(client, master, master_resort, "INACTIVE")

    assert response.status_code == 400


@pytest.mark.parametrize("new_status", CLOSED_STATUSES)
@pytest.mark.parametrize(
    "booking_status",
    [BookingStatusEnum.CANCELLED, BookingStatusEnum.COMPLETED, BookingStatusEnum.EXPIRED],
)
def test_update_resort_status_not_blocked_by_finished_bookings(
    client, container_engine, master, master_resort, create_booking, new_status, booking_status
):
    create_booking(master_resort, booking_status)

    response = set_status(client, master, master_resort, new_status)

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == new_status


@pytest.mark.parametrize("booking_status", [BookingStatusEnum.PENDING, BookingStatusEnum.CONFIRMED])
def test_update_resort_status_not_blocked_by_bookings_that_already_ended(
    client, container_engine, master, master_resort, create_booking, booking_status
):
    create_booking(master_resort, booking_status, check_out_in=timedelta(days=-1))

    response = set_status(client, master, master_resort, "INACTIVE")

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.INACTIVE


def test_update_resort_status_not_blocked_by_bookings_at_another_resort(
    client, container_engine, master, master_resort, other_resort, create_booking
):
    create_booking(other_resort)

    response = set_status(client, master, master_resort, "INACTIVE")

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.INACTIVE


def test_update_resort_status_not_blocked_by_bookings_at_a_sibling_resort(
    client, master, master_resort, master_draft_resort, create_booking
):
    create_booking(master_draft_resort)

    response = set_status(client, master, master_resort, "INACTIVE")

    assert response.status_code == 200


def test_update_resort_status_between_closed_statuses_is_not_blocked(
    client, db_session, container_engine, master, master_resort, create_booking
):
    """
    The block is about closing a live resort. A resort that is already closed can change between closed statuses.
    """

    create_booking(master_resort)

    master_resort.status = ResortStatusEnum.INACTIVE

    db_session.commit()

    response = set_status(client, master, master_resort, "MAINTENANCE")

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.MAINTENANCE


def test_update_resort_status_reopening_with_bookings_is_fine(
    client, db_session, container_engine, master, master_resort, create_booking
):
    create_booking(master_resort)

    master_resort.status = ResortStatusEnum.MAINTENANCE

    db_session.commit()

    response = set_status(client, master, master_resort, "ACTIVE")

    assert response.status_code == 200
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


# VALIDATION


@pytest.mark.parametrize("body", [{}, {"status": "CLOSED"}, {"status": ""}, {"status": None}, {"status": "active"}])
def test_update_resort_status_invalid_body(client, container_engine, master, master_resort, body):

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/status", master, body)

    assert response.status_code == 422
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


def test_update_resort_status_extra_field_is_rejected(client, container_engine, master, master_resort):
    body = {"status": "INACTIVE", "base_price_per_night": "1"}

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/status", master, body)

    assert response.status_code == 422
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


# WHO CAN CHANGE IT


def test_update_resort_status_resort_of_another_master(client, container_engine, other_master, master_resort):

    response = set_status(client, other_master, master_resort, "INACTIVE")

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


def test_update_resort_status_admin_of_another_resort(client, container_engine, master_resort, other_admin):

    response = set_status(client, other_admin, master_resort, "INACTIVE")

    assert response.status_code == 404
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE


def test_update_resort_status_admin_cannot_change_a_sibling_resort(
    client, container_engine, resort_admin, master_draft_resort
):
    """
    Same organization, but the admin only manages their own resort.
    """

    response = set_status(client, resort_admin, master_draft_resort, "ACTIVE")

    assert response.status_code == 404
    assert get_status(container_engine, master_draft_resort.id) == ResortStatusEnum.INACTIVE


def test_update_resort_status_unknown_resort(client, master):

    response = call(client, "PUT", f"{BASE_PATH}/999999/status", master, {"status": "ACTIVE"})

    assert response.status_code == 404


def test_update_resort_status_guest_is_not_allowed(client, guest, master_resort):

    response = set_status(client, guest, master_resort, "INACTIVE")

    assert response.status_code == 401


def test_update_resort_status_without_a_token(client, master_resort):

    response = set_status(client, None, master_resort, "INACTIVE")

    assert response.status_code == 401


def test_update_resort_status_removed_admin_token_is_refused(client, container_engine, master_resort, removed_admin):

    response = set_status(client, removed_admin, master_resort, "INACTIVE")

    assert response.status_code == 401
    assert get_status(container_engine, master_resort.id) == ResortStatusEnum.ACTIVE
