from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest_password_reset_request import GuestPasswordResetRequest
from core.services.password_reset_token_handler import PasswordResetTokenHandler
from domains.guest.auth.initiate_password_reset import GENERIC_MESSAGE
from tests.domains.guest.auth.do_sign_up_test import do_encrypt_data

path = "/test/api/v1/guest/auth/forgot-password"


@pytest.fixture
def send_email_task_mock(mocker):
    """
    Replaces the Celery task so no broker, worker or SMTP server is needed. The test only checks what was queued.
    """

    return mocker.patch("domains.guest.auth.initiate_password_reset.send_email_task")


def get_reset_requests(container_engine, guest_id: str) -> list[GuestPasswordResetRequest]:

    with Session(container_engine) as session:
        return list(
            session.scalars(
                select(GuestPasswordResetRequest)
                .where(GuestPasswordResetRequest.guest_id == guest_id)
                .order_by(GuestPasswordResetRequest.id)
            ).all()
        )


def do_forgot_password(client, email: str):

    return client.post(path, json={"data": do_encrypt_data({"email": email})})


def test_do_forgot_password(client, container_engine, guest, send_email_task_mock):

    response = do_forgot_password(client, guest.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    # A REQUEST THAT EXPIRES IN ABOUT AN HOUR IS SAVED

    reset_requests = get_reset_requests(container_engine, guest.id)

    assert len(reset_requests) == 1
    assert reset_requests[0].request_consumed_at is None
    assert (
        timedelta(minutes=59)
        < reset_requests[0].expires_at - datetime.now(tz=timezone.utc)
        <= timedelta(hours=1)
    )

    # THE EMAIL IS QUEUED ONCE FOR THE GUEST

    send_email_task_mock.delay.assert_called_once()

    email_request = send_email_task_mock.delay.call_args.args[0]

    assert email_request["to"] == guest.email_address
    assert email_request["template_name"] == "password_reset_email.html"
    assert email_request["html_substitutions"]["user_name"] == guest.first_name

    # THE LINK IN THE EMAIL HOLDS A TOKEN FOR THE SAVED REQUEST

    reset_url = email_request["html_substitutions"]["reset_url"]

    assert urlparse(reset_url).path == "/guest/auth/reset-password"

    token = parse_qs(urlparse(reset_url).query)["d"][0]

    assert PasswordResetTokenHandler(token=token).decode_reset_token() == reset_requests[0].id


def test_do_forgot_password_email_not_exist(client, container_engine, send_email_task_mock):
    """
    Must look exactly like a success so the endpoint cannot be used to find registered emails.
    """

    response = do_forgot_password(client, "not_exist@gmail.com")

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    with Session(container_engine) as session:
        assert session.scalars(select(GuestPasswordResetRequest)).all() == []

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_unverified_guest(client, container_engine, unverified_guest, send_email_task_mock):

    response = do_forgot_password(client, unverified_guest.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    assert get_reset_requests(container_engine, unverified_guest.id) == []

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_active_request_exists(
    client, container_engine, guest, password_reset_request, send_email_task_mock
):
    """
    The link that was already emailed still works, so no new request and no second email.
    """

    response = do_forgot_password(client, guest.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    assert len(get_reset_requests(container_engine, guest.id)) == 1

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_previous_request_expired(
    client, container_engine, guest, expired_password_reset_request, send_email_task_mock
):

    response = do_forgot_password(client, guest.email_address)

    assert response.status_code == 200

    assert len(get_reset_requests(container_engine, guest.id)) == 2

    send_email_task_mock.delay.assert_called_once()


def test_do_forgot_password_previous_request_consumed(
    client, container_engine, guest, consumed_password_reset_request, send_email_task_mock
):

    response = do_forgot_password(client, guest.email_address)

    assert response.status_code == 200

    assert len(get_reset_requests(container_engine, guest.id)) == 2

    send_email_task_mock.delay.assert_called_once()


def test_do_forgot_password_response_is_the_same_for_every_case(
    client, guest, unverified_guest, send_email_task_mock
):

    responses = [
        do_forgot_password(client, email)
        for email in (guest.email_address, unverified_guest.email_address, "not_exist@gmail.com")
    ]

    assert {response.status_code for response in responses} == {200}
    assert len({response.text for response in responses}) == 1

