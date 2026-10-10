from datetime import datetime, timezone, timedelta

import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.auth.do_sign_up_test import do_encrypt_data
from tests.domains.manager.resort.admin.conftest import admin_path, build_token, invite_payload
from tests.domains.manager.resort.helpers import BASE_PATH, call

RESET_PAGE = "/test/api/v1/manager/auth/reset-password"


def get_admin(container_engine, admin_id: str) -> Admin:

    with Session(container_engine) as session:
        return session.get(Admin, admin_id)


def open_reset_request(db_session, admin) -> ManagerPasswordResetRequest:
    """
    A password reset link the admin asked for and has not used.
    """

    db_session.add(
        reset_request := ManagerPasswordResetRequest(
            manager_id=admin.id, expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1)
        )
    )

    db_session.commit()

    return reset_request


def test_remove_admin(client, container_engine, master, master_resort, resort_admin):

    response = call(client, "DELETE", admin_path(master_resort), master)

    assert response.status_code == 200

    # THE RESPONSE IS THE RESORT, NOW WITHOUT AN ADMIN

    assert response.json()["resort"]["id"] == master_resort.id
    assert response.json()["resort"]["admin"] is None


def test_remove_admin_clears_the_person_and_keeps_the_row(
    client, container_engine, master, master_resort, resort_admin
):

    call(client, "DELETE", admin_path(master_resort), master)

    removed = get_admin(container_engine, resort_admin.id)

    # THE ROW STAYS AS A RECORD, BUT NOTHING ABOUT THE PERSON AND NOTHING THAT LETS THEM IN

    assert removed is not None
    assert removed.deleted_at is not None
    assert removed.first_name == "DELETED"
    assert removed.last_name == "ADMIN"
    assert removed.email_address is None
    assert removed.phone_number is None
    assert removed.hashed_password is None
    assert removed.profile_picture is None
    assert removed.active_token is None
    assert removed.resort_id is None


def test_remove_admin_a_pending_admin(client, container_engine, master, master_resort, pending_admin):

    response = call(client, "DELETE", admin_path(master_resort), master)

    assert response.status_code == 200
    assert response.json()["resort"]["admin"] is None
    assert get_admin(container_engine, pending_admin.id).deleted_at is not None


def test_remove_admin_token_of_the_removed_admin_is_refused(client, master, master_resort, resort_admin):

    assert call(client, "GET", BASE_PATH, resort_admin).status_code == 200

    call(client, "DELETE", admin_path(master_resort), master)

    assert call(client, "GET", BASE_PATH, resort_admin).status_code == 401
    assert call(client, "GET", f"{BASE_PATH}/{master_resort.id}", resort_admin).status_code == 401


def test_remove_admin_removed_admin_can_no_longer_log_in(client, master, master_resort, resort_admin):
    email = resort_admin.email_address

    call(client, "DELETE", admin_path(master_resort), master)

    response = client.post(
        "/test/api/v1/manager/auth/login",
        json={"data": do_encrypt_data({"email": email, "password": "admin1234"})},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_NOT_EXISTS.name


def test_remove_admin_open_links_stop_working(
    client, db_session, container_engine, master, master_resort, resort_admin
):
    """
    A password reset link the admin asked for before being removed must not bring the account back.
    """

    reset_request = open_reset_request(db_session, resort_admin)
    token = build_token(reset_request)

    call(client, "DELETE", admin_path(master_resort), master)

    page = client.get(RESET_PAGE, params={"d": token})

    assert page.status_code == 400
    assert "Link Expired" in page.text

    response = client.post(
        RESET_PAGE, data={"token": token, "new_password": "newpass123", "confirm_password": "newpass123"}
    )

    assert response.status_code == 400
    assert get_admin(container_engine, resort_admin.id).hashed_password is None


def test_remove_admin_unused_invite_link_stops_working(client, container_engine, master, master_resort, pending_admin):

    with Session(container_engine) as session:
        invite = session.scalars(select(ManagerPasswordResetRequest)).one()
        token = build_token(invite)

    call(client, "DELETE", admin_path(master_resort), master)

    response = client.post(
        RESET_PAGE, data={"token": token, "new_password": "newpass123", "confirm_password": "newpass123"}
    )

    assert response.status_code == 400

    with Session(container_engine) as session:
        admin = session.get(Admin, pending_admin.id)

        assert admin.hashed_password is None
        assert admin.verification.verified_at is None


def test_remove_admin_the_resort_can_get_a_new_admin(client, master, master_resort, resort_admin, send_email_task_mock):

    call(client, "DELETE", admin_path(master_resort), master)

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(email="second_admin@gmail.com"))

    assert response.status_code == 200
    assert response.json()["resort"]["admin"]["email"] == "second_admin@gmail.com"
    assert response.json()["resort"]["admin"]["id"] != resort_admin.id


def test_remove_admin_the_same_email_can_be_invited_again(
    client, master, master_resort, resort_admin, send_email_task_mock
):
    email = resort_admin.email_address

    call(client, "DELETE", admin_path(master_resort), master)

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(email=email))

    assert response.status_code == 200
    assert response.json()["resort"]["admin"]["email"] == email
    assert response.json()["resort"]["admin"]["status"] == "PENDING"
    assert response.json()["resort"]["admin"]["id"] != resort_admin.id


def test_remove_admin_the_same_email_can_sign_up_as_a_master(client, master, master_resort, resort_admin, mocker):
    email = resort_admin.email_address

    call(client, "DELETE", admin_path(master_resort), master)

    mocker.patch("domains.manager.auth.sign_up_service.send_email_task")

    response = client.post(
        "/test/api/v1/manager/auth/signup",
        json={
            "data": do_encrypt_data(
                {
                    "email": email,
                    "first_name": "Former",
                    "last_name": "Admin",
                    "password": "master1234",
                    "phone": "",
                    "organization_name": "FORMER_ADMIN_ORGANIZATION",
                }
            )
        },
    )

    assert response.status_code == 200


def test_remove_admin_second_removal(client, master, master_resort, resort_admin):

    call(client, "DELETE", admin_path(master_resort), master)

    response = call(client, "DELETE", admin_path(master_resort), master)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.ADMIN_DOES_NOT_EXIST.name


def test_remove_admin_resort_has_no_admin(client, master, master_resort):

    response = call(client, "DELETE", admin_path(master_resort), master)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.ADMIN_DOES_NOT_EXIST.name


def test_remove_admin_leaves_everything_else_alone(
    client, container_engine, master, master_resort, resort_admin, other_admin, other_resort
):

    call(client, "DELETE", admin_path(master_resort), master)

    # THE ADMIN OF ANOTHER MASTER IS UNTOUCHED AND CAN STILL LOG IN WITH THEIR PASSWORD

    other = get_admin(container_engine, other_admin.id)

    assert other.deleted_at is None
    assert other.resort_id == other_resort.id
    assert bcrypt.checkpw("admin1234".encode("utf-8"), other.hashed_password)

    # AND THE RESORT KEEPS ITS DETAILS

    detail = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master).json()["resort"]

    assert detail["name"] == master_resort.name
    assert detail["status"] == master_resort.status
