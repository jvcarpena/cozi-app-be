from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from core.models.resort import Resort
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.resort.helpers import BASE_PATH, call


def get_resort(container_engine, resort_id: int) -> Resort:

    with Session(container_engine) as session:
        return session.get(Resort, resort_id)


def test_update_resort_detail_master(client, container_engine, master, master_resort):
    body = {
        "name": "Renamed Resort",
        "description": "New description",
        "max_guests": 40,
        "num_bedrooms": 8,
        "num_bathrooms": 6,
        "address": "New address",
        "latitude": "14.1907",
        "longitude": "121.1607",
    }

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, body)
    resort = response.json()["resort"]

    assert response.status_code == 200

    # THE RESPONSE IS THE UPDATED RESORT

    assert resort["name"] == "Renamed Resort"
    assert resort["description"] == "New description"
    assert resort["max_guests"] == 40
    assert resort["num_bedrooms"] == 8
    assert resort["num_bathrooms"] == 6
    assert resort["address"] == "New address"
    assert Decimal(resort["latitude"]) == Decimal("14.1907")
    assert Decimal(resort["longitude"]) == Decimal("121.1607")

    saved = get_resort(container_engine, master_resort.id)

    assert saved.name == "Renamed Resort"
    assert saved.max_guests == 40
    assert saved.address == "New address"


def test_update_resort_detail_admin_can_update_their_resort(client, container_engine, master_resort, resort_admin):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", resort_admin, {"description": "By the admin"})

    assert response.status_code == 200
    assert get_resort(container_engine, master_resort.id).description == "By the admin"


def test_update_resort_detail_only_the_fields_sent_change(client, container_engine, master, master_resort):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"max_guests": 7})

    assert response.status_code == 200

    saved = get_resort(container_engine, master_resort.id)

    assert saved.max_guests == 7
    assert saved.name == master_resort.name
    assert saved.description == master_resort.description
    assert saved.address == master_resort.address
    assert saved.num_bedrooms == master_resort.num_bedrooms


def test_update_resort_detail_does_not_touch_prices_or_status(client, container_engine, master, master_resort):

    call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": "Renamed Resort"})

    saved = get_resort(container_engine, master_resort.id)

    assert saved.base_price_per_night == master_resort.base_price_per_night
    assert saved.base_price_per_day_use == master_resort.base_price_per_day_use
    assert saved.status == master_resort.status


def test_update_resort_detail_trims_the_text(client, container_engine, master, master_resort):

    call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": "  Renamed  ", "address": "  Here  "})

    saved = get_resort(container_engine, master_resort.id)

    assert saved.name == "Renamed"
    assert saved.address == "Here"


def test_update_resort_detail_coordinates_can_be_removed(client, container_engine, master, master_resort):
    path = f"{BASE_PATH}/{master_resort.id}"

    call(client, "PATCH", path, master, {"latitude": "14.1907", "longitude": "121.1607"})
    response = call(client, "PATCH", path, master, {"latitude": None, "longitude": None})

    assert response.status_code == 200

    saved = get_resort(container_engine, master_resort.id)

    assert saved.latitude is None
    assert saved.longitude is None


def test_update_resort_detail_keep_the_same_name(client, master, master_resort):
    """
    Sending the name the resort already has is not a clash with itself.
    """

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": master_resort.name})

    assert response.status_code == 200


def test_update_resort_detail_name_taken_by_another_resort_of_the_organization(
    client, container_engine, master, master_resort, master_draft_resort
):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": master_draft_resort.name})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name
    assert get_resort(container_engine, master_resort.id).name == master_resort.name


def test_update_resort_detail_name_can_match_a_resort_of_another_organization(
    client, master, master_resort, other_resort
):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": other_resort.name})

    assert response.status_code == 200


def test_update_resort_detail_name_race_is_stopped_by_the_database(
    client, container_engine, master, master_resort, master_draft_resort, mocker
):

    mocker.patch("domains.manager.resort.update_resort_detail_service.check_resort_name_is_free")

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": master_draft_resort.name})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name
    assert get_resort(container_engine, master_resort.id).name == master_resort.name


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"name": None},
        {"name": ""},
        {"name": "   "},
        {"name": "a" * 257},
        {"description": None},
        {"description": ""},
        {"address": None},
        {"address": "  "},
        {"max_guests": None},
        {"max_guests": 0},
        {"max_guests": -3},
        {"max_guests": 1001},
        {"num_bedrooms": 0},
        {"num_bedrooms": None},
        {"num_bathrooms": 0},
        {"latitude": "10"},
        {"longitude": "10"},
        {"latitude": "91", "longitude": "10"},
        {"latitude": "10", "longitude": "181"},
        {"latitude": "10", "longitude": None},
        {"latitude": None, "longitude": "10"},
    ],
    ids=lambda body: ",".join(f"{key}={value}"[:40] for key, value in body.items()) or "empty body",
)
def test_update_resort_detail_invalid_body(client, container_engine, master, master_resort, body):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, body)

    assert response.status_code == 422

    # NOTHING CHANGED

    saved = get_resort(container_engine, master_resort.id)

    assert saved.name == master_resort.name
    assert saved.description == master_resort.description
    assert saved.max_guests == master_resort.max_guests
    assert saved.address == master_resort.address


@pytest.mark.parametrize(
    "field,value",
    [
        ("base_price_per_night", "99999"),
        ("base_price_per_day_use", "99999"),
        ("currency", "PHP"),
        ("status", "ACTIVE"),
        ("organization_id", 12345),
        ("id", 12345),
    ],
)
def test_update_resort_detail_fields_with_their_own_endpoint_are_rejected(
    client, container_engine, master, master_resort, field, value
):
    """
    A field the endpoint does not handle is refused, not silently ignored, so the client never believes a price
    or a status was changed when it was not.
    """

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", master, {"name": "Renamed", field: value})

    assert response.status_code == 422

    saved = get_resort(container_engine, master_resort.id)

    assert saved.name == master_resort.name
    assert saved.base_price_per_night == master_resort.base_price_per_night
    assert saved.status == master_resort.status
    assert saved.organization_id == master_resort.organization_id


def test_update_resort_detail_resort_of_another_master(client, container_engine, other_master, master_resort):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", other_master, {"name": "Hijacked"})

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name
    assert get_resort(container_engine, master_resort.id).name == master_resort.name


def test_update_resort_detail_admin_of_another_resort(client, container_engine, master_resort, other_admin):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", other_admin, {"name": "Hijacked"})

    assert response.status_code == 404
    assert get_resort(container_engine, master_resort.id).name == master_resort.name


def test_update_resort_detail_admin_cannot_update_a_sibling_resort(
    client, container_engine, resort_admin, master_draft_resort
):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_draft_resort.id}", resort_admin, {"name": "Hijacked"})

    assert response.status_code == 404
    assert get_resort(container_engine, master_draft_resort.id).name == master_draft_resort.name


def test_update_resort_detail_unknown_resort(client, master):

    response = call(client, "PATCH", f"{BASE_PATH}/999999", master, {"name": "Nothing"})

    assert response.status_code == 404


def test_update_resort_detail_guest_is_not_allowed(client, guest, master_resort):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", guest, {"name": "Hijacked"})

    assert response.status_code == 401


def test_update_resort_detail_without_a_token(client, master_resort):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", None, {"name": "Hijacked"})

    assert response.status_code == 401


def test_update_resort_detail_removed_admin_token_is_refused(client, container_engine, master_resort, removed_admin):

    response = call(client, "PATCH", f"{BASE_PATH}/{master_resort.id}", removed_admin, {"name": "Hijacked"})

    assert response.status_code == 401
    assert get_resort(container_engine, master_resort.id).name == master_resort.name
