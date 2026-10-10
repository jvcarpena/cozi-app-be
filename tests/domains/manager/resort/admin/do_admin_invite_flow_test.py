from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.manager_password_reset_request import ManagerLinkPurpose, ManagerPasswordResetRequest
from tests.domains.manager.auth.do_sign_up_test import do_encrypt_data
from tests.domains.manager.resort.admin.conftest import admin_path, build_token, invite_payload, token_in_email
from tests.domains.manager.resort.helpers import BASE_PATH, call

RESET_PAGE = "/test/api/v1/manager/auth/reset-password"
LOGIN = "/test/api/v1/manager/auth/login"


def login(client, email: str, password: str):

    return client.post(LOGIN, json={"data": do_encrypt_data({"email": email, "password": password})})


def test_admin_invite_from_the_invite_to_the_first_login(client, master, master_resort, send_email_task_mock):
    """
    The whole life of an invite: the master invites, the admin sets a password from the emailed link, logs in,
    works on their resort, and the master removes them.
    """

    # 1. THE MASTER INVITES THE ADMIN. THEY CANNOT LOG IN YET.

    call(client, "POST", admin_path(master_resort), master, invite_payload(email="flow_admin@gmail.com"))

    token = token_in_email(send_email_task_mock.delay.call_args.args[0])

    assert login(client, "flow_admin@gmail.com", "chosen1234").status_code == 400

    # 2. THE ADMIN OPENS THE LINK AND SEES THE PAGE FOR SETTING A FIRST PASSWORD

    page = client.get(RESET_PAGE, params={"d": token})

    assert page.status_code == 200
    assert "Set Your Password" in page.text
    assert "Reset Your Password" not in page.text.split("<h1")[1]

    # 3. THE ADMIN CHOOSES A PASSWORD

    done = client.post(
        RESET_PAGE, data={"token": token, "new_password": "chosen1234", "confirm_password": "chosen1234"}
    )

    assert done.status_code == 200
    assert "Your Account Is Ready" in done.text

    # 4. THEY LOG IN AS THE ADMIN OF THE RESORT, WITH NO ORGANIZATION

    response = login(client, "flow_admin@gmail.com", "chosen1234")
    body = response.json()

    assert response.status_code == 200
    assert body["role"] == "admin"
    assert body["resort_id"] == master_resort.id
    assert body["organization_id"] is None

    # 5. THEY SEE ONLY THEIR RESORT, AND IT SHOWS THEM AS ACTIVE TO THE MASTER

    admin_headers = {"Authorization": body["token"]}

    listing = client.get(BASE_PATH, headers=admin_headers)

    assert [resort["id"] for resort in listing.json()["resorts"]] == [master_resort.id]
    assert (
        call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master).json()["resort"]["admin"]["status"] == "ACTIVE"
    )

    # 6. THE LINK WORKS ONLY ONCE

    again = client.post(
        RESET_PAGE, data={"token": token, "new_password": "other12345", "confirm_password": "other12345"}
    )

    assert again.status_code == 400
    assert login(client, "flow_admin@gmail.com", "other12345").status_code == 400

    # 7. THE MASTER REMOVES THE ADMIN. THE TOKEN THEY STILL HOLD IS REFUSED AND THEY CANNOT LOG IN.

    call(client, "DELETE", admin_path(master_resort), master)

    assert client.get(BASE_PATH, headers=admin_headers).status_code == 401
    assert login(client, "flow_admin@gmail.com", "chosen1234").status_code == 400


def test_admin_invite_page_keeps_the_invite_wording_after_a_mistake(
    client, master, master_resort, send_email_task_mock
):

    call(client, "POST", admin_path(master_resort), master, invite_payload())

    token = token_in_email(send_email_task_mock.delay.call_args.args[0])

    response = client.post(
        RESET_PAGE, data={"token": token, "new_password": "chosen1234", "confirm_password": "different1"}
    )

    assert response.status_code == 400
    assert "Set Your Password" in response.text
    assert "do not match" in response.text


def test_admin_invite_link_expires_after_7_days(client, db_session, master, master_resort, pending_admin):

    invite = db_session.scalars(select(ManagerPasswordResetRequest)).one()
    token = build_token(invite)

    assert client.get(RESET_PAGE, params={"d": token}).status_code == 200

    invite.expires_at = datetime.now(tz=timezone.utc) - timedelta(minutes=1)

    db_session.commit()

    page = client.get(RESET_PAGE, params={"d": build_token(invite)})

    assert page.status_code == 400
    assert "Link Expired" in page.text
    assert "ask the owner" in page.text


def test_password_reset_page_keeps_the_reset_wording(client, db_session, resort_admin):
    """
    A verified admin who forgot their password gets a reset link, and its page is about resetting.
    """

    db_session.add(
        reset_request := ManagerPasswordResetRequest(
            manager_id=resort_admin.id, expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1)
        )
    )

    db_session.commit()

    page = client.get(RESET_PAGE, params={"d": build_token(reset_request)})

    assert page.status_code == 200
    assert reset_request.purpose == ManagerLinkPurpose.RESET
    assert "Reset Your Password" in page.text
    assert "Set Your Password" not in page.text


def test_password_reset_link_of_an_admin_shows_the_reset_success_page(client, db_session, resort_admin):

    db_session.add(
        reset_request := ManagerPasswordResetRequest(
            manager_id=resort_admin.id, expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1)
        )
    )

    db_session.commit()

    response = client.post(
        RESET_PAGE,
        data={"token": build_token(reset_request), "new_password": "newpass123", "confirm_password": "newpass123"},
    )

    assert response.status_code == 200
    assert "Password Updated!" in response.text
    assert "Your Account Is Ready" not in response.text


def test_forgot_password_creates_a_reset_link_not_an_invite(client, container_engine, resort_admin, mocker):

    mocker.patch("domains.manager.auth.initiate_password_reset.send_email_task")

    response = client.post(
        "/test/api/v1/manager/auth/forgot-password",
        json={"data": do_encrypt_data({"email": resort_admin.email_address})},
    )

    assert response.status_code == 200

    with Session(container_engine) as session:
        [reset_request] = session.scalars(select(ManagerPasswordResetRequest)).all()

        assert reset_request.purpose == ManagerLinkPurpose.RESET


def test_forgot_password_ignores_the_invite_link_of_a_pending_admin(client, container_engine, pending_admin, mocker):
    """
    A pending admin has no password to forget. They get the generic answer and no email, they ask the master
    to send the invite again.
    """

    send = mocker.patch("domains.manager.auth.initiate_password_reset.send_email_task")

    response = client.post(
        "/test/api/v1/manager/auth/forgot-password",
        json={"data": do_encrypt_data({"email": pending_admin.email_address})},
    )

    assert response.status_code == 200
    send.delay.assert_not_called()

    with Session(container_engine) as session:
        assert len(session.scalars(select(ManagerPasswordResetRequest)).all()) == 1
