import pytest

from core.models.resort import Resort
from sqlalchemy.orm import Session

from tests.domains.manager.resort.helpers import BASE_PATH, call

# EVERY ENDPOINT THAT WORKS ON ONE RESORT, AS (NAME, METHOD, PATH AFTER THE RESORT ID, BODY).
# THE SAME ACTORS ARE TRIED AGAINST ALL OF THEM, SO A NEW ENDPOINT THAT FORGETS THE OWNERSHIP CHECK IS EASY TO SPOT.

RESORT_ENDPOINTS = [
    ("detail", "GET", "", None),
    ("update", "PATCH", "", {"name": "Hijacked"}),
    ("pricing", "PUT", "/pricing", {"base_price_per_night": "1", "base_price_per_day_use": "1", "currency": "PHP"}),
    ("status", "PUT", "/status", {"status": "INACTIVE"}),
]

ENDPOINT_IDS = [endpoint[0] for endpoint in RESORT_ENDPOINTS]


def assert_resort_untouched(container_engine, resort: Resort):

    with Session(container_engine) as session:
        saved = session.get(Resort, resort.id)

        assert saved.name == resort.name
        assert saved.status == resort.status
        assert saved.base_price_per_night == resort.base_price_per_night
        assert saved.base_price_per_day_use == resort.base_price_per_day_use


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_master_of_another_organization_gets_a_404(
    client, container_engine, other_master, master_resort, name, method, suffix, body
):

    response = call(client, method, f"{BASE_PATH}/{master_resort.id}{suffix}", other_master, body)

    assert response.status_code == 404
    assert response.json()["detail"] == "RESORT_DOES_NOT_EXIST"
    assert_resort_untouched(container_engine, master_resort)


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_admin_of_another_resort_is_refused(
    client, container_engine, other_admin, master_resort, name, method, suffix, body
):
    """
    A 404, except for the master-only pricing endpoint where an admin is refused before the resort is even looked at.
    """

    response = call(client, method, f"{BASE_PATH}/{master_resort.id}{suffix}", other_admin, body)

    assert response.status_code == (403 if name == "pricing" else 404)
    assert_resort_untouched(container_engine, master_resort)


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_admin_cannot_reach_a_sibling_resort_of_the_same_organization(
    client, container_engine, resort_admin, master_draft_resort, name, method, suffix, body
):

    response = call(client, method, f"{BASE_PATH}/{master_draft_resort.id}{suffix}", resort_admin, body)

    assert response.status_code == (403 if name == "pricing" else 404)
    assert_resort_untouched(container_engine, master_draft_resort)


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_guest_token_is_refused(client, container_engine, guest, master_resort, name, method, suffix, body):

    response = call(client, method, f"{BASE_PATH}/{master_resort.id}{suffix}", guest, body)

    assert response.status_code == 401
    assert_resort_untouched(container_engine, master_resort)


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_no_token_is_refused(client, container_engine, master_resort, name, method, suffix, body):

    response = call(client, method, f"{BASE_PATH}/{master_resort.id}{suffix}", None, body)

    assert response.status_code == 401
    assert_resort_untouched(container_engine, master_resort)


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_removed_admin_token_is_refused(
    client, container_engine, master_resort, removed_admin, name, method, suffix, body
):

    response = call(client, method, f"{BASE_PATH}/{master_resort.id}{suffix}", removed_admin, body)

    assert response.status_code == 401
    assert_resort_untouched(container_engine, master_resort)


@pytest.mark.parametrize("name,method,suffix,body", RESORT_ENDPOINTS, ids=ENDPOINT_IDS)
def test_unknown_resort_looks_the_same_as_someone_elses(
    client, other_master, master_resort, name, method, suffix, body
):
    """
    A resort that is not yours and a resort that does not exist give the same answer.
    """

    not_yours = call(client, method, f"{BASE_PATH}/{master_resort.id}{suffix}", other_master, body)
    missing = call(client, method, f"{BASE_PATH}/999999{suffix}", other_master, body)

    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.json() == missing.json()
