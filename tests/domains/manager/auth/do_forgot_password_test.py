from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, parse_qs

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from core.services.password_reset_token_handler import MANAGER_PURPOSE, PasswordResetTokenHandler
from domains.manager.auth.initiate_password_reset import GENERIC_MESSAGE
from tests.domains.manager.auth.do_sign_up_test import do_encrypt_data

path = "/test/api/v1/manager/auth/forgot-password"


@pytest.fixture
def send_email_task_mock(mocker):
    """
    Replaces the Celery task so no broker, worker or SMTP server is needed. The test only checks what was queued.
    """

    return mocker.patch("domains.manager.auth.initiate_password_reset.send_email_task")


def get_reset_requests(container_engine, manager_id: str) -> list[ManagerPasswordResetRequest]:

    with Session(container_engine) as session:
        return list(
            session.scalars(
                select(ManagerPasswordResetRequest)
                .where(ManagerPasswordResetRequest.manager_id == manager_id)
                .order_by(ManagerPasswordResetRequest.id)
            ).all()
        )


def do_forgot_password(client, email: str):

    return client.post(path, json={"data": do_encrypt_data({"email": email})})


def test_do_forgot_password(client, container_engine, manager, send_email_task_mock):

    response = do_forgot_password(client, manager.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    # A REQUEST THAT EXPIRES IN ABOUT AN HOUR IS SAVED

    reset_requests = get_reset_requests(container_engine, manager.id)

    assert len(reset_requests) == 1
    assert reset_requests[0].request_consumed_at is None
    assert timedelta(minutes=59) < reset_requests[0].expires_at - datetime.now(tz=timezone.utc) <= timedelta(hours=1)

    # THE EMAIL IS QUEUED ONCE FOR THE MANAGER

    send_email_task_mock.delay.assert_called_once()

    email_request = send_email_task_mock.delay.call_args.args[0]

    assert email_request["to"] == manager.email_address
    assert email_request["template_name"] == "password_reset_email.html"
    assert email_request["html_substitutions"]["user_name"] == manager.first_name

    # THE LINK POINTS AT THE MANAGER RESET PAGE AND HOLDS A MANAGER TOKEN FOR THE SAVED REQUEST

    reset_url = email_request["html_substitutions"]["reset_url"]

    assert urlparse(reset_url).path == "/manager/auth/reset-password"

    token = parse_qs(urlparse(reset_url).query)["d"][0]

    assert PasswordResetTokenHandler(token=token, purpose=MANAGER_PURPOSE).decode_reset_token() == (
        reset_requests[0].id
    )


def test_do_forgot_password_email_not_exist(client, container_engine, send_email_task_mock):
    """
    Must look exactly like a success so the endpoint cannot be used to find registered emails.
    """

    response = do_forgot_password(client, "not_exist@gmail.com")

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    with Session(container_engine) as session:
        assert session.scalars(select(ManagerPasswordResetRequest)).all() == []

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_guest_email(client, container_engine, guest, send_email_task_mock):
    """
    A guest is not a manager, so a guest email gets the same response and no email.
    """

    response = do_forgot_password(client, guest.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    with Session(container_engine) as session:
        assert session.scalars(select(ManagerPasswordResetRequest)).all() == []

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_unverified_manager(client, container_engine, unverified_manager, send_email_task_mock):

    response = do_forgot_password(client, unverified_manager.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    assert get_reset_requests(container_engine, unverified_manager.id) == []

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_active_request_exists(
    client, container_engine, manager, password_reset_request, send_email_task_mock
):
    """
    The link that was already emailed still works, so no new request and no second email.
    """

    response = do_forgot_password(client, manager.email_address)

    assert response.status_code == 200
    assert response.json() == {"message": GENERIC_MESSAGE}

    assert len(get_reset_requests(container_engine, manager.id)) == 1

    send_email_task_mock.delay.assert_not_called()


def test_do_forgot_password_previous_request_expired(
    client, container_engine, manager, expired_password_reset_request, send_email_task_mock
):

    response = do_forgot_password(client, manager.email_address)

    assert response.status_code == 200

    assert len(get_reset_requests(container_engine, manager.id)) == 2

    send_email_task_mock.delay.assert_called_once()


def test_do_forgot_password_previous_request_consumed(
    client, container_engine, manager, consumed_password_reset_request, send_email_task_mock
):

    response = do_forgot_password(client, manager.email_address)

    assert response.status_code == 200

    assert len(get_reset_requests(container_engine, manager.id)) == 2

    send_email_task_mock.delay.assert_called_once()


def test_do_forgot_password_response_is_the_same_for_every_case(
    client, manager, unverified_manager, send_email_task_mock
):

    responses = [
        do_forgot_password(client, email)
        for email in (manager.email_address, unverified_manager.email_address, "not_exist@gmail.com")
    ]

    assert {response.status_code for response in responses} == {200}
    assert len({response.text for response in responses}) == 1
