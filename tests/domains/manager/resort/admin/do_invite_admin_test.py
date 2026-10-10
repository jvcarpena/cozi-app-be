from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import ULID

from core.models.admin import Admin
from core.models.manager_password_reset_request import ManagerLinkPurpose, ManagerPasswordResetRequest
from core.services.password_reset_token_handler import MANAGER_PURPOSE, PasswordResetTokenHandler
from domains.manager.enums import ManagerErrorMessage
from domains.manager.resort.admin import invite_admin_service
from tests.domains.manager.resort.admin.conftest import admin_path, invite_payload, token_in_email
from tests.domains.manager.resort.conftest import create_admin
from tests.domains.manager.resort.helpers import BASE_PATH, call


def get_admins(container_engine) -> list[Admin]:

    with Session(container_engine) as session:
        return list(session.scalars(select(Admin).order_by(Admin.id)).all())


def get_requests(container_engine) -> list[ManagerPasswordResetRequest]:

    with Session(container_engine) as session:
        return list(session.scalars(select(ManagerPasswordResetRequest).order_by(ManagerPasswordResetRequest.id)).all())


def test_invite_admin(client, container_engine, master, master_resort, send_email_task_mock):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload())

    assert response.status_code == 200

    # THE RESPONSE IS THE RESORT, WITH THE ADMIN WHO WAS JUST INVITED

    admin = response.json()["resort"]["admin"]

    assert response.json()["resort"]["id"] == master_resort.id
    assert admin["status"] == "PENDING"
    assert admin["email"] == "new_admin@gmail.com"
    assert admin["first_name"] == "Maria"
    assert admin["last_name"] == "Santos"

    # THE ADMIN IS SAVED WITHOUT A PASSWORD, FOR THIS RESORT, AND NOT VERIFIED

    with Session(container_engine) as session:
        saved = list(session.scalars(select(Admin).order_by(Admin.id)).all())[0]

        assert saved.id == admin["id"]
        assert len(saved.id) == 26 and ULID.from_str(saved.id)
        assert saved.user_type == "admin"
        assert saved.resort_id == master_resort.id
        assert saved.hashed_password is None
        assert saved.phone_number == "09171234567"
        assert saved.deleted_at is None
        assert saved.verification.verified_at is None


def test_invite_admin_saves_an_invite_link_that_lasts_7_days(
    client, container_engine, master, master_resort, send_email_task_mock
):

    call(client, "POST", admin_path(master_resort), master, invite_payload())

    [invite] = get_requests(container_engine)

    assert invite.purpose == ManagerLinkPurpose.INVITE
    assert invite.request_consumed_at is None
    assert timedelta(days=6, hours=23) < invite.expires_at - datetime.now(tz=timezone.utc) <= timedelta(days=7)


def test_invite_admin_queues_one_email_with_a_working_link(
    client, container_engine, master, master_resort, send_email_task_mock
):

    call(client, "POST", admin_path(master_resort), master, invite_payload())

    send_email_task_mock.delay.assert_called_once()

    email_request = send_email_task_mock.delay.call_args.args[0]
    substitutions = email_request["html_substitutions"]

    assert email_request["to"] == "new_admin@gmail.com"
    assert email_request["template_name"] == "admin_invite_email.html"
    assert master_resort.name in email_request["subject"]
    assert substitutions["user_name"] == "Maria"
    assert substitutions["inviter_name"] == f"{master.first_name} {master.last_name}"
    assert substitutions["resort_name"] == master_resort.name
    assert substitutions["expires_in_days"] == 7
    assert "/manager/auth/reset-password?d=" in substitutions["invite_url"]

    # THE TOKEN IN THE LINK BELONGS TO THE SAVED INVITE AND IS SIGNED FOR MANAGERS

    [invite] = get_requests(container_engine)

    token = token_in_email(email_request)

    assert PasswordResetTokenHandler(token=token, purpose=MANAGER_PURPOSE).decode_reset_token() == invite.id


def test_invite_admin_trims_names_and_empty_phone_is_no_phone(
    client, container_engine, master, master_resort, send_email_task_mock
):

    response = call(
        client,
        "POST",
        admin_path(master_resort),
        master,
        invite_payload(first_name="  Maria  ", last_name="  De La Cruz  ", phone="   "),
    )

    assert response.status_code == 200

    saved = get_admins(container_engine)[0]

    assert saved.first_name == "Maria"
    assert saved.last_name == "De La Cruz"
    assert saved.phone_number is None


def test_invite_admin_without_a_phone(client, container_engine, master, master_resort, send_email_task_mock):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(phone=None))

    assert response.status_code == 200
    assert get_admins(container_engine)[0].phone_number is None


def test_invite_admin_to_a_draft_resort(client, master, master_draft_resort, send_email_task_mock):
    """
    A master can staff a resort before it goes live.
    """

    response = call(client, "POST", admin_path(master_draft_resort), master, invite_payload())

    assert response.status_code == 200
    assert response.json()["resort"]["status"] == "INACTIVE"


def test_invite_admin_is_shown_in_the_resort_detail_as_pending(client, master, master_resort, send_email_task_mock):

    call(client, "POST", admin_path(master_resort), master, invite_payload())

    response = call(client, "GET", f"{BASE_PATH}/{master_resort.id}", master)

    assert response.json()["resort"]["admin"]["status"] == "PENDING"


def test_invite_admin_does_not_change_other_resorts(
    client, container_engine, master, master_resort, master_draft_resort, send_email_task_mock
):

    call(client, "POST", admin_path(master_resort), master, invite_payload())

    detail = call(client, "GET", f"{BASE_PATH}/{master_draft_resort.id}", master)

    assert detail.json()["resort"]["admin"] is None
    assert [admin.resort_id for admin in get_admins(container_engine)] == [master_resort.id]


# A RESORT HAS AT MOST ONE ADMIN


def test_invite_admin_resort_already_has_an_active_admin(
    client, container_engine, master, master_resort, resort_admin, send_email_task_mock
):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_ALREADY_HAS_ADMIN.name
    assert [admin.id for admin in get_admins(container_engine)] == [resort_admin.id]
    send_email_task_mock.delay.assert_not_called()


def test_invite_admin_resort_already_has_a_pending_admin(
    client, container_engine, master, master_resort, pending_admin, send_email_task_mock
):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_ALREADY_HAS_ADMIN.name
    assert [admin.id for admin in get_admins(container_engine)] == [pending_admin.id]
    send_email_task_mock.delay.assert_not_called()


def test_invite_admin_two_invites_at_the_same_moment(
    client, container_engine, master, master_resort, resort_admin, send_email_task_mock, mocker
):
    """
    Both requests can pass the "no admin yet" check together. The unique resort_id of the database stops the second
    one, and the answer is the same clean error, not a 500.
    """

    original = invite_admin_service.get_resort_admin
    calls = []

    def first_check_sees_no_admin(session, resort_id, for_update=False):

        calls.append(resort_id)

        return None if len(calls) == 1 else original(session, resort_id, for_update)

    mocker.patch(
        "domains.manager.resort.admin.invite_admin_service.get_resort_admin", side_effect=first_check_sees_no_admin
    )

    response = call(client, "POST", admin_path(master_resort), master, invite_payload())

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.RESORT_ALREADY_HAS_ADMIN.name
    assert [admin.id for admin in get_admins(container_engine)] == [resort_admin.id]
    send_email_task_mock.delay.assert_not_called()


# THE EMAIL


def test_invite_admin_email_of_a_master(client, container_engine, master, master_resort, send_email_task_mock):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(email=master.email_address))

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_REGISTERED.name
    assert get_admins(container_engine) == []
    send_email_task_mock.delay.assert_not_called()


def test_invite_admin_email_of_an_admin_of_another_resort(
    client, master, master_resort, other_admin, send_email_task_mock
):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(email=other_admin.email_address))

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_REGISTERED.name


def test_invite_admin_email_of_an_admin_who_is_still_pending(
    client, master, master_resort, master_draft_resort, db_session, send_email_task_mock
):
    """
    An invite that has not been accepted still holds the email.
    """

    from tests.domains.manager.resort.admin.conftest import create_pending_admin

    pending = create_pending_admin(db_session, master_draft_resort, invite_sent_minutes_ago=10)

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(email=pending.email_address))

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_REGISTERED.name


def test_invite_admin_email_of_a_removed_admin_is_free(
    client, db_session, container_engine, master, master_resort, send_email_task_mock
):
    """
    A removed admin has no resort and is marked deleted, so the same person can be invited again.
    """

    create_admin(db_session, "old_admin", "returning_admin@gmail.com", None, deleted_at=datetime.now(tz=timezone.utc))

    response = call(
        client, "POST", admin_path(master_resort), master, invite_payload(email="returning_admin@gmail.com")
    )

    assert response.status_code == 200

    live = [admin for admin in get_admins(container_engine) if admin.deleted_at is None]

    assert [admin.email_address for admin in live] == ["returning_admin@gmail.com"]


def test_invite_admin_email_of_a_guest_is_allowed(client, master, master_resort, guest, send_email_task_mock):
    """
    A guest and a manager are different accounts, a guest's email is not taken for managers.
    """

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(email=guest.email_address))

    assert response.status_code == 200


# VALIDATION


@pytest.mark.parametrize(
    "overrides,status_code",
    [
        ({"first_name": "Mar1a"}, 400),
        ({"last_name": "Santos3"}, 400),
        ({"first_name": "M@ria"}, 400),
        ({"first_name": ""}, 422),
        ({"last_name": "   "}, 422),
        ({"first_name": "a" * 51}, 422),
        ({"email": "not-an-email"}, 422),
        ({"email": ""}, 422),
        ({"phone": "1" * 51}, 422),
        ({"email": None}, 422),
        ({"first_name": None}, 422),
        ({"last_name": None}, 422),
        ({"password": "secret123"}, 422),
        ({"resort_id": 1}, 422),
        ({"status": "ACTIVE"}, 422),
    ],
    ids=lambda value: (
        ",".join(f"{key}={str(val)[:20]}" for key, val in value.items()) if isinstance(value, dict) else str(value)
    ),
)
def test_invite_admin_invalid_body(
    client, container_engine, master, master_resort, send_email_task_mock, overrides, status_code
):

    response = call(client, "POST", admin_path(master_resort), master, invite_payload(**overrides))

    assert response.status_code == status_code

    # NOTHING WAS SAVED AND NOTHING WAS SENT

    assert get_admins(container_engine) == []
    assert get_requests(container_engine) == []
    send_email_task_mock.delay.assert_not_called()


def test_invite_admin_without_a_body(client, master, master_resort, send_email_task_mock):

    response = call(client, "POST", admin_path(master_resort), master)

    assert response.status_code == 422
    send_email_task_mock.delay.assert_not_called()
