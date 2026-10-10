from datetime import datetime, timezone
from decimal import Decimal

from core.models.resort import ResortStatusEnum
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.resort.helpers import BASE_PATH, call


def test_get_resort_detail_master(client, master, master_resort):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master)
    resort = response.json()["resort"]

    assert response.status_code == 200
    assert resort["id"] == master_resort.id
    assert resort["organization_id"] == master.organization_id
    assert resort["name"] == master_resort.name
    assert resort["status"] == ResortStatusEnum.ACTIVE
    assert resort["description"] == master_resort.description
    assert Decimal(resort["base_price_per_night"]) == master_resort.base_price_per_night
    assert Decimal(resort["base_price_per_day_use"]) == master_resort.base_price_per_day_use
    assert resort["currency"] == "PHP"
    assert resort["max_guests"] == master_resort.max_guests
    assert resort["num_bedrooms"] == master_resort.num_bedrooms
    assert resort["num_bathrooms"] == master_resort.num_bathrooms
    assert resort["address"] == master_resort.address
    assert resort["latitude"] is None
    assert resort["longitude"] is None


def test_get_resort_detail_master_without_an_admin(client, master, master_resort):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master)

    assert response.json()["resort"]["admin"] is None


def test_get_resort_detail_master_sees_the_admin(client, master, master_resort, resort_admin):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master)

    assert response.json()["resort"]["admin"] == {
        "id": resort_admin.id,
        "status": "ACTIVE",
        "email": resort_admin.email_address,
        "first_name": resort_admin.first_name,
        "last_name": resort_admin.last_name,
    }


def test_get_resort_detail_removed_admin_is_not_shown(client, master, master_resort, removed_admin):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master)

    assert response.status_code == 200
    assert response.json()["resort"]["admin"] is None


def test_get_resort_detail_admin_sees_their_resort_without_admin_info(client, master_resort, resort_admin):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", resort_admin)

    assert response.status_code == 200
    assert response.json()["resort"]["id"] == master_resort.id
    assert response.json()["resort"]["admin"] is None


def test_get_resort_detail_draft_resort(client, master, master_draft_resort):

    response = call(client, "GET", f"{BASE_PATH}/{master_draft_resort.id}", master)

    assert response.status_code == 200
    assert response.json()["resort"]["status"] == ResortStatusEnum.INACTIVE


def test_get_resort_detail_resort_of_another_master(client, master, other_resort):
    """
    Same answer as a resort that does not exist, so a manager cannot tell which ids are taken.
    """

    response = call(client, "GET", f"{BASE_PATH}/{other_resort.id}", master)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name


def test_get_resort_detail_other_master_cannot_read_it(client, other_master, master_resort, resort_admin):
    """
    Nothing about the resort leaks, including the name and email of its admin.
    """

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", other_master)

    assert response.status_code == 404
    assert resort_admin.email_address not in response.text


def test_get_resort_detail_admin_of_another_resort(client, master_resort, other_admin):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", other_admin)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name


def test_get_resort_detail_admin_cannot_read_a_sibling_resort(client, resort_admin, master_draft_resort):
    """
    Same organization, but the admin only manages their own resort.
    """

    response = call(client, "GET", f"{BASE_PATH}/{master_draft_resort.id}", resort_admin)

    assert response.status_code == 404


def test_get_resort_detail_unknown_resort(client, master):

    response = call(client, "GET", f"{BASE_PATH}/999999", master)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name


def test_get_resort_detail_removed_resort(client, db_session, master, master_resort):

    master_resort.deleted_at = datetime.now(tz=timezone.utc)

    db_session.commit()

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master)

    assert response.status_code == 404


def test_get_resort_detail_resort_id_is_not_a_number(client, master):

    response = call(client, "GET", f"{BASE_PATH}/not-a-number", master)

    assert response.status_code == 422


def test_get_resort_detail_guest_is_not_allowed(client, guest, master_resort):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", guest)

    assert response.status_code == 401


def test_get_resort_detail_without_a_token(client, master_resort):

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", None)

    assert response.status_code == 401
