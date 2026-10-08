from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.models.resort import Resort, ResortStatusEnum
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.resort.helpers import BASE_PATH, call, resort_payload


def get_resorts(container_engine) -> list[Resort]:

    with Session(container_engine) as session:
        return list(session.scalars(select(Resort).order_by(Resort.id)).all())


def test_create_resort(client, container_engine, master):

    response = call(client, "POST", BASE_PATH, master, resort_payload())
    resort = response.json()["resort"]

    assert response.status_code == 200

    # THE RESPONSE IS THE NEW RESORT, SO THE CLIENT KNOWS ITS ID

    assert resort["id"] is not None
    assert resort["name"] == "Sunrise Resort"
    assert resort["description"] == "Beachfront resort with a private pool."
    assert Decimal(resort["base_price_per_night"]) == Decimal("25000.50")
    assert Decimal(resort["base_price_per_day_use"]) == Decimal("12000")
    assert resort["currency"] == "PHP"
    assert resort["max_guests"] == 20
    assert resort["num_bedrooms"] == 4
    assert resort["num_bathrooms"] == 3
    assert resort["address"] == "Pansol, Calamba, Laguna"
    assert resort["latitude"] is None
    assert resort["longitude"] is None
    assert resort["admin"] is None

    # THE RESORT IS SAVED AS A DRAFT IN THE ORGANIZATION OF THE MASTER

    assert resort["status"] == ResortStatusEnum.INACTIVE
    assert resort["organization_id"] == master.organization_id

    saved = get_resorts(container_engine)

    assert len(saved) == 1
    assert saved[0].id == resort["id"]
    assert saved[0].status == ResortStatusEnum.INACTIVE
    assert saved[0].organization_id == master.organization_id


def test_create_resort_can_be_read_back_with_the_returned_id(client, master):

    resort_id = call(client, "POST", BASE_PATH, master, resort_payload()).json()["resort"]["id"]

    response = call(client, "GET", f"{BASE_PATH}/{resort_id}", master)

    assert response.status_code == 200
    assert response.json()["resort"]["id"] == resort_id


def test_create_resort_with_coordinates(client, master):
    payload = resort_payload(latitude="14.1907", longitude="121.1607")

    response = call(client, "POST", BASE_PATH, master, payload)

    assert response.status_code == 200
    assert Decimal(response.json()["resort"]["latitude"]) == Decimal("14.1907")
    assert Decimal(response.json()["resort"]["longitude"]) == Decimal("121.1607")


def test_create_resort_trims_the_text(client, container_engine, master):
    payload = resort_payload(name="  Sunrise Resort  ", description="  Nice  ", address="  Pansol  ")

    response = call(client, "POST", BASE_PATH, master, payload)

    assert response.status_code == 200

    saved = get_resorts(container_engine)[0]

    assert saved.name == "Sunrise Resort"
    assert saved.description == "Nice"
    assert saved.address == "Pansol"


def test_create_resort_accepts_the_highest_price(client, master):
    payload = resort_payload(base_price_per_night="9999999.9999", base_price_per_day_use="9999999.9999")

    response = call(client, "POST", BASE_PATH, master, payload)

    assert response.status_code == 200
    assert Decimal(response.json()["resort"]["base_price_per_night"]) == Decimal("9999999.9999")


def test_create_resort_organization_and_status_cannot_be_chosen(client, container_engine, master, other_master):
    """
    The resort always goes to the organization of the master who is logged in, and always starts as a draft.
    """

    for extra in ({"organization_id": other_master.organization_id}, {"status": "ACTIVE"}):

        response = call(client, "POST", BASE_PATH, master, resort_payload(**extra))

        assert response.status_code == 422

    assert get_resorts(container_engine) == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "   "},
        {"name": "a" * 257},
        {"description": ""},
        {"description": "   "},
        {"address": ""},
        {"address": "   "},
        {"base_price_per_night": "0"},
        {"base_price_per_night": "-1"},
        {"base_price_per_night": "10000000"},
        {"base_price_per_night": "123456789012"},
        {"base_price_per_night": "1.00001"},
        {"base_price_per_night": "abc"},
        {"base_price_per_day_use": "0"},
        {"base_price_per_day_use": "10000000"},
        {"currency": "USD"},
        {"currency": "php"},
        {"max_guests": 0},
        {"max_guests": 1001},
        {"max_guests": "many"},
        {"num_bedrooms": 0},
        {"num_bedrooms": 101},
        {"num_bathrooms": 0},
        {"latitude": "91", "longitude": "10"},
        {"latitude": "-91", "longitude": "10"},
        {"latitude": "10", "longitude": "181"},
        {"latitude": "10", "longitude": "-181"},
        {"latitude": "10"},
        {"longitude": "10"},
    ],
    ids=lambda overrides: ",".join(f"{key}={value}"[:40] for key, value in overrides.items()),
)
def test_create_resort_invalid_value(client, container_engine, master, overrides):

    response = call(client, "POST", BASE_PATH, master, resort_payload(**overrides))

    assert response.status_code == 422

    # NOTHING WAS SAVED

    assert get_resorts(container_engine) == []


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "description",
        "base_price_per_night",
        "base_price_per_day_use",
        "currency",
        "max_guests",
        "num_bedrooms",
        "num_bathrooms",
        "address",
    ],
)
def test_create_resort_missing_field(client, container_engine, master, field):

    response = call(client, "POST", BASE_PATH, master, resort_payload(**{field: None}))

    assert response.status_code == 422
    assert get_resorts(container_engine) == []


def test_create_resort_without_a_body(client, master):

    response = call(client, "POST", BASE_PATH, master)

    assert response.status_code == 422


def test_create_resort_name_already_taken_in_the_organization(client, container_engine, master, master_resort):

    response = call(client, "POST", BASE_PATH, master, resort_payload(name=master_resort.name))

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name

    assert len(get_resorts(container_engine)) == 1


def test_create_resort_name_taken_ignores_spaces_around_it(client, master, master_resort):

    response = call(client, "POST", BASE_PATH, master, resort_payload(name=f"   {master_resort.name}   "))

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name


def test_create_resort_name_can_be_used_by_another_organization(client, container_engine, master, other_resort):
    """
    Names are unique inside an organization only. Another master already has a resort with this name.
    """

    response = call(client, "POST", BASE_PATH, master, resort_payload(name=other_resort.name))

    assert response.status_code == 200
    assert len(get_resorts(container_engine)) == 2


def test_create_resort_name_race_is_stopped_by_the_database(client, container_engine, master, master_resort, mocker):
    """
    Two requests can both pass the name check at the same moment. The unique constraint of the database must
    still stop the second one, with the same error, not a 500.
    """

    mocker.patch("domains.manager.resort.create_resort_service.check_resort_name_is_free")

    response = call(client, "POST", BASE_PATH, master, resort_payload(name=master_resort.name))

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name

    assert len(get_resorts(container_engine)) == 1


def test_resort_name_is_unique_in_the_database(db_session, master, master_resort):

    db_session.add(
        Resort(
            organization_id=master.organization_id,
            name=master_resort.name,
            status=ResortStatusEnum.INACTIVE,
            description="D",
            base_price_per_night=Decimal("1"),
            base_price_per_day_use=Decimal("1"),
            currency="PHP",
            max_guests=1,
            num_bedrooms=1,
            num_bathrooms=1,
            address="A",
        )
    )

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_create_resort_several_resorts_for_one_master(client, container_engine, master):

    for name in ("First Resort", "Second Resort", "Third Resort"):

        assert call(client, "POST", BASE_PATH, master, resort_payload(name=name)).status_code == 200

    saved = get_resorts(container_engine)

    assert [resort.name for resort in saved] == ["First Resort", "Second Resort", "Third Resort"]
    assert {resort.organization_id for resort in saved} == {master.organization_id}


def test_create_resort_admin_is_not_allowed(client, container_engine, resort_admin):
    """
    Only a master creates resorts. An admin is logged in with a valid token but has no right to do this.
    """

    response = call(client, "POST", BASE_PATH, resort_admin, resort_payload())

    assert response.status_code == 403
    assert response.json()["detail"] == "MASTER_ONLY"

    assert [resort.id for resort in get_resorts(container_engine)] == [resort_admin.resort_id]


def test_create_resort_guest_is_not_allowed(client, container_engine, guest):

    response = call(client, "POST", BASE_PATH, guest, resort_payload())

    assert response.status_code == 401
    assert get_resorts(container_engine) == []


def test_create_resort_without_a_token(client, container_engine):

    response = call(client, "POST", BASE_PATH, None, resort_payload())

    assert response.status_code == 401
    assert get_resorts(container_engine) == []


def test_create_resort_removed_master_token_is_refused(client, db_session, container_engine, master):
    master.deleted_at = datetime.now(tz=timezone.utc)

    db_session.commit()

    response = call(client, "POST", BASE_PATH, master, resort_payload())

    assert response.status_code == 401
    assert get_resorts(container_engine) == []
