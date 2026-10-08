from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from core.models.booking import Booking
from core.models.resort import Resort
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.resort.helpers import BASE_PATH, call

NEW_PRICES = {"base_price_per_night": "31500.75", "base_price_per_day_use": "15000", "currency": "PHP"}


def get_resort(container_engine, resort_id: int) -> Resort:

    with Session(container_engine) as session:
        return session.get(Resort, resort_id)


def test_update_resort_pricing(client, container_engine, master, master_resort):

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, NEW_PRICES)
    resort = response.json()["resort"]

    assert response.status_code == 200

    # THE RESPONSE IS THE UPDATED RESORT

    assert Decimal(resort["base_price_per_night"]) == Decimal("31500.75")
    assert Decimal(resort["base_price_per_day_use"]) == Decimal("15000")
    assert resort["currency"] == "PHP"

    # AND THE NEW PRICES ARE REALLY SAVED

    saved = get_resort(container_engine, master_resort.id)

    assert saved.base_price_per_night == Decimal("31500.75")
    assert saved.base_price_per_day_use == Decimal("15000")


def test_update_resort_pricing_changes_nothing_else(client, container_engine, master, master_resort):

    call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, NEW_PRICES)

    saved = get_resort(container_engine, master_resort.id)

    assert saved.name == master_resort.name
    assert saved.description == master_resort.description
    assert saved.status == master_resort.status
    assert saved.max_guests == master_resort.max_guests
    assert saved.address == master_resort.address


def test_update_resort_pricing_other_resorts_keep_their_prices(
    client, container_engine, master, master_resort, master_draft_resort
):

    call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, NEW_PRICES)

    saved = get_resort(container_engine, master_draft_resort.id)

    assert saved.base_price_per_night == master_draft_resort.base_price_per_night
    assert saved.base_price_per_day_use == master_draft_resort.base_price_per_day_use


def test_update_resort_pricing_can_be_read_back_afterwards(client, master, master_resort):
    """
    Guards against an update that damages the Resort model itself: every later request must still work.
    """

    path = f"{BASE_PATH}/{master_resort.id}"

    call(client, "PUT", f"{path}/pricing", master, NEW_PRICES)

    detail = call(client, "GET", path, master)
    listing = call(client, "GET", BASE_PATH, master)

    assert detail.status_code == 200
    assert Decimal(detail.json()["resort"]["base_price_per_night"]) == Decimal("31500.75")
    assert listing.status_code == 200
    assert Decimal(listing.json()["resorts"][0]["base_price_per_night"]) == Decimal("31500.75")


def test_update_resort_pricing_existing_bookings_keep_their_price(
    client, container_engine, master, master_resort, create_booking
):

    booking = create_booking(master_resort)

    call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, NEW_PRICES)

    with Session(container_engine) as session:
        assert session.get(Booking, booking.id).total_price == booking.total_price


def test_update_resort_pricing_the_guest_sees_the_new_price(client, master, master_resort):

    call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, NEW_PRICES)

    response = client.get(f"/test/api/v1/guest/resorts/{master_resort.id}")

    assert response.status_code == 200
    assert Decimal(response.json()["data"]["base_price_per_night"]) == Decimal("31500.75")


def test_update_resort_pricing_admin_is_not_allowed(client, container_engine, master_resort, resort_admin):
    """
    Only a master changes prices. The admin is logged in with a valid token and still manages this resort.
    """

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", resort_admin, NEW_PRICES)

    assert response.status_code == 403
    assert response.json()["detail"] == "MASTER_ONLY"

    saved = get_resort(container_engine, master_resort.id)

    assert saved.base_price_per_night == master_resort.base_price_per_night
    assert saved.base_price_per_day_use == master_resort.base_price_per_day_use


@pytest.mark.parametrize(
    "overrides",
    [
        {"base_price_per_night": "0"},
        {"base_price_per_night": "-5"},
        {"base_price_per_night": "10000000"},
        {"base_price_per_night": "123456789012"},
        {"base_price_per_night": "1.00001"},
        {"base_price_per_night": "free"},
        {"base_price_per_day_use": "0"},
        {"base_price_per_day_use": "10000000"},
        {"currency": "USD"},
        {"currency": ""},
        {"status": "ACTIVE"},
        {"name": "Renamed"},
    ],
    ids=lambda overrides: ",".join(f"{key}={value}" for key, value in overrides.items()),
)
def test_update_resort_pricing_invalid_body(client, container_engine, master, master_resort, overrides):

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, {**NEW_PRICES, **overrides})

    assert response.status_code == 422

    saved = get_resort(container_engine, master_resort.id)

    assert saved.base_price_per_night == master_resort.base_price_per_night
    assert saved.base_price_per_day_use == master_resort.base_price_per_day_use


@pytest.mark.parametrize("field", ["base_price_per_night", "base_price_per_day_use", "currency"])
def test_update_resort_pricing_missing_field(client, container_engine, master, master_resort, field):
    body = {key: value for key, value in NEW_PRICES.items() if key != field}

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", master, body)

    assert response.status_code == 422
    assert get_resort(container_engine, master_resort.id).base_price_per_night == master_resort.base_price_per_night


def test_update_resort_pricing_resort_of_another_master(client, container_engine, other_master, master_resort):

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", other_master, NEW_PRICES)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name
    assert get_resort(container_engine, master_resort.id).base_price_per_night == master_resort.base_price_per_night


def test_update_resort_pricing_unknown_resort(client, master):

    response = call(client, "PUT", f"{BASE_PATH}/999999/pricing", master, NEW_PRICES)

    assert response.status_code == 404


def test_update_resort_pricing_guest_is_not_allowed(client, guest, master_resort):

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", guest, NEW_PRICES)

    assert response.status_code == 401


def test_update_resort_pricing_without_a_token(client, master_resort):

    response = call(client, "PUT", f"{BASE_PATH}/{master_resort.id}/pricing", None, NEW_PRICES)

    assert response.status_code == 401
