from datetime import datetime, timezone, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.manager_password_reset_request import ManagerLinkPurpose, ManagerPasswordResetRequest
from core.models.manager_verification import ManagerVerification
from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.resort.admin.conftest import admin_path, build_token, token_in_email
from tests.domains.manager.resort.helpers import call

RESET_PAGE = "/test/api/v1/manager/auth/reset-password"


def get_requests(container_engine, admin_id: str) -> list[ManagerPasswordResetRequest]:

    with Session(container_engine) as session:
        return list(
            session.scalars(
                select(ManagerPasswordResetRequest)
                .where(ManagerPasswordResetRequest.manager_id == admin_id)
                .order_by(ManagerPasswordResetRequest.id)
            ).all()
        )


def get_verification(container_engine, admin_id: str) -> ManagerVerification:

    with Session(container_engine) as session:
        return session.get(ManagerVerification, admin_id)


def test_resend_admin_invite(client, container_engine, master, master_resort, pending_admin, send_email_task_mock):

    response = call(client, "POST", admin_path(master_resort, "/resend"), master)

    assert response.status_code == 200
    assert response.json()["resort"]["admin"]["id"] == pending_admin.id
    assert response.json()["resort"]["admin"]["status"] == "PENDING"

    # ONE NEW EMAIL FOR THE SAME ADMIN

    send_email_task_mock.delay.assert_called_once()

    email_request = send_email_task_mock.delay.call_args.args[0]

    assert email_request["to"] == pending_admin.email_address
    assert email_request["template_name"] == "admin_invite_email.html"
    assert email_request["html_substitutions"]["expires_in_days"] == 7


def test_resend_admin_invite_old_link_stops_and_new_link_works(
    client, container_engine, master, master_resort, pending_admin, send_email_task_mock
):
    [old_request] = get_requests(container_engine, pending_admin.id)
    old_token = build_token(old_request)

    assert client.get(RESET_PAGE, params={"d": old_token}).status_code == 200

    call(client, "POST", admin_path(master_resort, "/resend"), master)

    new_token = token_in_email(send_email_task_mock.delay.call_args.args[0])

    old_page = client.get(RESET_PAGE, params={"d": old_token})
    new_page = client.get(RESET_PAGE, params={"d": new_token})

    assert old_page.status_code == 400
    assert "Link Expired" in old_page.text
    assert new_page.status_code == 200
    assert "Set Your Password" in new_page.text


def test_resend_admin_invite_saves_a_new_invite_and_closes_the_old_one(
    client, container_engine, master, master_resort, pending_admin, send_email_task_mock
):

    call(client, "POST", admin_path(master_resort, "/resend"), master)

    old_request, new_request = get_requests(container_engine, pending_admin.id)

    assert old_request.request_consumed_at is not None
    assert new_request.request_consumed_at is None
    assert new_request.purpose == ManagerLinkPurpose.INVITE
    assert timedelta(days=6, hours=23) < new_request.expires_at - datetime.now(tz=timezone.utc) <= timedelta(days=7)


def test_resend_admin_invite_updates_the_time_it_was_sent(
    client, container_engine, master, master_resort, pending_admin, send_email_task_mock
):

    call(client, "POST", admin_path(master_resort, "/resend"), master)

    verification = get_verification(container_engine, pending_admin.id)

    assert datetime.now(tz=timezone.utc) - verification.latest_email_sent_at < timedelta(minutes=1)
    assert verification.verified_at is None


def test_resend_admin_invite_cooldown(
    client, container_engine, master, master_resort, recently_invited_admin, send_email_task_mock
):
    """
    The invite was sent a minute ago, so it can't be sent again yet. The link that was already sent still works.
    """

    [old_request] = get_requests(container_engine, recently_invited_admin.id)

    response = call(client, "POST", admin_path(master_resort, "/resend"), master)

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.INVITE_RECENTLY_SENT.name

    send_email_task_mock.delay.assert_not_called()

    requests = get_requests(container_engine, recently_invited_admin.id)

    assert len(requests) == 1
    assert requests[0].request_consumed_at is None
    assert client.get(RESET_PAGE, params={"d": build_token(old_request)}).status_code == 200


def test_resend_admin_invite_twice_in_a_row(client, master, master_resort, pending_admin, send_email_task_mock):
    """
    The first resend starts the cooldown, so the second one is refused.
    """

    first = call(client, "POST", admin_path(master_resort, "/resend"), master)
    second = call(client, "POST", admin_path(master_resort, "/resend"), master)

    assert first.status_code == 200
    assert second.status_code == 400
    assert second.json()["detail"] == ManagerErrorMessage.INVITE_RECENTLY_SENT.name
    assert send_email_task_mock.delay.call_count == 1


def test_resend_admin_invite_admin_already_set_a_password(
    client, container_engine, master, master_resort, resort_admin, send_email_task_mock
):

    response = call(client, "POST", admin_path(master_resort, "/resend"), master)

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.ADMIN_ALREADY_ACTIVE.name
    assert get_requests(container_engine, resort_admin.id) == []
    send_email_task_mock.delay.assert_not_called()


def test_resend_admin_invite_resort_has_no_admin(client, master, master_resort, send_email_task_mock):

    response = call(client, "POST", admin_path(master_resort, "/resend"), master)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.ADMIN_DOES_NOT_EXIST.name
    send_email_task_mock.delay.assert_not_called()


def test_resend_admin_invite_removed_admin_is_not_found(
    client, master, master_resort, removed_admin, send_email_task_mock
):

    response = call(client, "POST", admin_path(master_resort, "/resend"), master)

    assert response.status_code == 404
    assert response.json()["detail"] == ManagerErrorMessage.ADMIN_DOES_NOT_EXIST.name
    send_email_task_mock.delay.assert_not_called()
