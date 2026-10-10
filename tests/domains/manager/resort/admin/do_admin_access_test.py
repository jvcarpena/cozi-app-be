import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from tests.domains.manager.resort.admin.conftest import admin_path, invite_payload
from tests.domains.manager.resort.helpers import call

# THE THREE ADMIN ENDPOINTS, AS (NAME, METHOD, PATH AFTER /admin, BODY). ONLY A MASTER, AND ONLY FOR THEIR OWN RESORT.

ADMIN_ENDPOINTS = [
    ("invite", "POST", "", invite_payload(email="intruder@gmail.com")),
    ("resend", "POST", "/resend", None),
    ("remove", "DELETE", "", None),
]

ENDPOINT_IDS = [endpoint[0] for endpoint in ADMIN_ENDPOINTS]


def assert_admins_untouched(container_engine, expected_admin_ids: list[str]):

    with Session(container_engine) as session:
        admins = session.scalars(select(Admin).order_by(Admin.id)).all()

        assert sorted(admin.id for admin in admins) == sorted(expected_admin_ids)
        assert all(admin.deleted_at is None for admin in admins)


@pytest.mark.parametrize("name,method,suffix,body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_master_of_another_organization_gets_a_404(
    client,
    container_engine,
    other_master,
    master_resort,
    resort_admin,
    send_email_task_mock,
    name,
    method,
    suffix,
    body,
):

    response = call(client, method, admin_path(master_resort, suffix), other_master, body)

    assert response.status_code == 404
    assert response.json()["detail"] == "RESORT_DOES_NOT_EXIST"
    assert_admins_untouched(container_engine, [resort_admin.id])
    send_email_task_mock.delay.assert_not_called()


@pytest.mark.parametrize("name,method,suffix,body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_the_admin_of_the_resort_is_refused(
    client, container_engine, master_resort, resort_admin, send_email_task_mock, name, method, suffix, body
):
    """
    An admin cannot manage admins, not even their own resort's. The token is valid, only the role is wrong.
    """

    response = call(client, method, admin_path(master_resort, suffix), resort_admin, body)

    assert response.status_code == 403
    assert response.json()["detail"] == "MASTER_ONLY"
    assert_admins_untouched(container_engine, [resort_admin.id])
    send_email_task_mock.delay.assert_not_called()


@pytest.mark.parametrize("name,method,suffix,body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_the_admin_of_another_resort_is_refused(
    client, container_engine, master_resort, resort_admin, other_admin, send_email_task_mock, name, method, suffix, body
):

    response = call(client, method, admin_path(master_resort, suffix), other_admin, body)

    assert response.status_code == 403
    assert_admins_untouched(container_engine, [resort_admin.id, other_admin.id])


@pytest.mark.parametrize("name,method,suffix,body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_guest_token_is_refused(
    client, container_engine, guest, master_resort, resort_admin, send_email_task_mock, name, method, suffix, body
):

    response = call(client, method, admin_path(master_resort, suffix), guest, body)

    assert response.status_code == 401
    assert_admins_untouched(container_engine, [resort_admin.id])


@pytest.mark.parametrize("name,method,suffix,body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_no_token_is_refused(
    client, container_engine, master_resort, resort_admin, send_email_task_mock, name, method, suffix, body
):

    response = call(client, method, admin_path(master_resort, suffix), None, body)

    assert response.status_code == 401
    assert_admins_untouched(container_engine, [resort_admin.id])


@pytest.mark.parametrize("name,method,suffix,body", ADMIN_ENDPOINTS, ids=ENDPOINT_IDS)
def test_unknown_resort_looks_the_same_as_someone_elses(
    client, other_master, master_resort, send_email_task_mock, name, method, suffix, body
):

    not_yours = call(client, method, admin_path(master_resort, suffix), other_master, body)
    missing = call(client, method, f"/test/api/v1/manager/resorts/999999/admin{suffix}", other_master, body)

    assert not_yours.status_code == missing.status_code == 404
    assert not_yours.json() == missing.json()


def test_a_master_cannot_invite_to_the_resort_of_another_master(
    client, container_engine, master, other_resort, send_email_task_mock
):

    response = call(client, "POST", admin_path(other_resort), master, invite_payload())

    assert response.status_code == 404
    assert_admins_untouched(container_engine, [])
