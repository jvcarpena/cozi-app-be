from datetime import datetime, timezone
from decimal import Decimal

from core.models.resort import ResortStatusEnum
from tests.domains.manager.resort.helpers import BASE_PATH, call


def listed_ids(response) -> list[int]:

    return [resort["id"] for resort in response.json()["resorts"]]


def test_get_resorts_master_sees_every_resort_of_the_organization(
    client, master, master_resort, master_draft_resort, other_resort
):

    response = call(client, "GET", BASE_PATH, master)

    assert response.status_code == 200

    # BOTH OF THE MASTER'S RESORTS, DRAFT INCLUDED, NEWEST FIRST. THE RESORT OF THE OTHER MASTER IS NOT THERE.

    assert listed_ids(response) == [master_draft_resort.id, master_resort.id]


def test_get_resorts_item_fields(client, master, master_resort):

    response = call(client, "GET", BASE_PATH, master)
    item = response.json()["resorts"][0]

    assert item == {
        "id": master_resort.id,
        "name": master_resort.name,
        "status": ResortStatusEnum.ACTIVE,
        "address": master_resort.address,
        "base_price_per_night": item["base_price_per_night"],
        "base_price_per_day_use": item["base_price_per_day_use"],
    }
    assert Decimal(item["base_price_per_night"]) == master_resort.base_price_per_night
    assert Decimal(item["base_price_per_day_use"]) == master_resort.base_price_per_day_use


def test_get_resorts_admin_sees_only_the_resort_they_manage(
    client, resort_admin, master_resort, master_draft_resort, other_resort
):
    """
    The admin belongs to the same organization as master_draft_resort, but only manages master_resort.
    """

    response = call(client, "GET", BASE_PATH, resort_admin)

    assert response.status_code == 200
    assert listed_ids(response) == [master_resort.id]


def test_get_resorts_other_master_sees_only_their_own(
    client, other_master, master_resort, master_draft_resort, other_resort
):

    response = call(client, "GET", BASE_PATH, other_master)

    assert listed_ids(response) == [other_resort.id]


def test_get_resorts_master_without_resorts(client, master):

    response = call(client, "GET", BASE_PATH, master)

    assert response.status_code == 200
    assert response.json() == {"resorts": []}


def test_get_resorts_admin_without_a_resort(client, db_session, resort_admin, master_resort):
    """
    An admin that is not assigned to a resort sees nothing, not every resort with an empty owner.
    """

    resort_admin.resort_id = None

    db_session.commit()

    response = call(client, "GET", BASE_PATH, resort_admin)

    assert response.status_code == 200
    assert response.json() == {"resorts": []}


def test_get_resorts_hides_removed_resorts(client, db_session, master, master_resort, master_draft_resort):

    master_draft_resort.deleted_at = datetime.now(tz=timezone.utc)

    db_session.commit()

    response = call(client, "GET", BASE_PATH, master)

    assert listed_ids(response) == [master_resort.id]


def test_get_resorts_guest_is_not_allowed(client, guest, master_resort):

    response = call(client, "GET", BASE_PATH, guest)

    assert response.status_code == 401


def test_get_resorts_without_a_token(client, master_resort):

    response = call(client, "GET", BASE_PATH, None)

    assert response.status_code == 401


def test_get_resorts_removed_admin_token_is_refused(client, removed_admin):

    response = call(client, "GET", BASE_PATH, removed_admin)

    assert response.status_code == 401
