from datetime import datetime, timezone, timedelta

import bcrypt
import pytest

from core.models.guest_password_reset_request import GuestPasswordResetRequest
from core.services.auth_token_handler import AuthTokenHandler
from domains.guest.enums import GuestErrorMessage
from tests.domains.guest.auth.do_sign_up_test import do_encrypt_data
from tests.domains.guest.auth.password_reset_helpers import build_reset_token

path = "/test/api/v1/guest/auth/reset-password"

NEW_PASSWORD = "newpass123"

LINK_EXPIRED_TITLE = "Link Expired"


def do_reset_password(client, token: str, new_password: str = NEW_PASSWORD, confirm_password: str | None = None):

    return client.post(
        path,
        data={
            "token": token,
            "new_password": new_password,
            "confirm_password": new_password if confirm_password is None else confirm_password,
        },
    )


def is_password(guest, password: str) -> bool:

    return bcrypt.checkpw(password.encode("utf-8"), guest.hashed_password)


# GET RESET PASSWORD PAGE


def test_do_get_reset_password_page(client, password_reset_request):
    token = build_reset_token(password_reset_request)

    response = client.get(path, params={"d": token})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Reset Your Password - Cozi</title>" in response.text
    assert f'name="token" value="{token}"' in response.text
    assert 'name="new_password"' in response.text
    assert 'name="confirm_password"' in response.text
    assert LINK_EXPIRED_TITLE not in response.text


def test_do_get_reset_password_page_expired(client, expired_password_reset_request):

    response = client.get(path, params={"d": build_reset_token(expired_password_reset_request)})

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text
    assert 'name="new_password"' not in response.text


def test_do_get_reset_password_page_consumed(client, consumed_password_reset_request):

    response = client.get(path, params={"d": build_reset_token(consumed_password_reset_request)})

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text


def test_do_get_reset_password_page_request_not_exist(client, password_reset_request):
    """
    A valid token that points to a request that is not in the database.
    """

    token = build_reset_token(
        GuestPasswordResetRequest(
            id=password_reset_request.id + 100, expires_at=datetime.now(tz=timezone.utc) + timedelta(hours=1)
        )
    )

    response = client.get(path, params={"d": token})

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text


def test_do_get_reset_password_page_invalid_token(client):

    response = client.get(path, params={"d": "not-a-valid-token"})

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text


def test_do_get_reset_password_page_login_token_rejected(client, guest):
    """
    A login token must not be usable as a password reset token.
    """

    response = client.get(path, params={"d": AuthTokenHandler(user_id=guest.id).generate_auth_token()})

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text


def test_do_get_reset_password_page_without_token(client):

    response = client.get(path)

    assert response.status_code == 422


# POST RESET PASSWORD


def test_do_reset_password(client, db_session, guest, password_reset_request):

    response = do_reset_password(client, build_reset_token(password_reset_request))

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Password Updated - Cozi</title>" in response.text

    # THE PASSWORD IS CHANGED AND THE REQUEST IS CONSUMED

    db_session.expire_all()

    assert is_password(guest, NEW_PASSWORD)
    assert not is_password(guest, "guest1234")
    assert password_reset_request.request_consumed_at is not None


def test_do_reset_password_can_login_with_new_password(client, guest, password_reset_request):

    do_reset_password(client, build_reset_token(password_reset_request))

    login_path = "/test/api/v1/guest/auth/login"

    new_password_response = client.post(
        login_path, json={"data": do_encrypt_data({"email": guest.email_address, "password": NEW_PASSWORD})}
    )
    old_password_response = client.post(
        login_path, json={"data": do_encrypt_data({"email": guest.email_address, "password": "guest1234"})}
    )

    assert new_password_response.status_code == 200
    assert old_password_response.status_code == 400
    assert old_password_response.json()["detail"] == GuestErrorMessage.INVALID_CREDENTIALS.name


def test_do_reset_password_link_can_only_be_used_once(client, db_session, guest, password_reset_request):
    token = build_reset_token(password_reset_request)

    first_response = do_reset_password(client, token)
    second_response = do_reset_password(client, token, new_password="another1234")

    assert first_response.status_code == 200
    assert second_response.status_code == 400
    assert LINK_EXPIRED_TITLE in second_response.text

    db_session.expire_all()

    assert is_password(guest, NEW_PASSWORD)


def test_do_reset_password_mismatch(client, db_session, guest, password_reset_request):

    response = do_reset_password(
        client, build_reset_token(password_reset_request), new_password=NEW_PASSWORD, confirm_password="different1234"
    )

    # THE FORM IS SHOWN AGAIN WITH THE ERROR AND THE LINK STAYS USABLE

    assert response.status_code == 400
    assert GuestErrorMessage.PASSWORD_MISMATCH.value in response.text
    assert 'name="new_password"' in response.text

    db_session.expire_all()

    assert is_password(guest, "guest1234")
    assert password_reset_request.request_consumed_at is None


@pytest.mark.parametrize("new_password", ["12345", "a" * 73])
def test_do_reset_password_invalid_length(client, db_session, guest, password_reset_request, new_password):

    response = do_reset_password(client, build_reset_token(password_reset_request), new_password=new_password)

    assert response.status_code == 400
    assert GuestErrorMessage.INVALID_PASSWORD_LENGTH.value in response.text
    assert 'name="new_password"' in response.text

    db_session.expire_all()

    assert is_password(guest, "guest1234")
    assert password_reset_request.request_consumed_at is None


@pytest.mark.parametrize("new_password", ["123456", "a" * 72])
def test_do_reset_password_length_limits_accepted(client, db_session, guest, password_reset_request, new_password):

    response = do_reset_password(client, build_reset_token(password_reset_request), new_password=new_password)

    assert response.status_code == 200

    db_session.expire_all()

    assert is_password(guest, new_password)


def test_do_reset_password_expired(client, db_session, guest, expired_password_reset_request):

    response = do_reset_password(client, build_reset_token(expired_password_reset_request))

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text

    db_session.expire_all()

    assert is_password(guest, "guest1234")


def test_do_reset_password_consumed(client, db_session, guest, consumed_password_reset_request):

    response = do_reset_password(client, build_reset_token(consumed_password_reset_request))

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text

    db_session.expire_all()

    assert is_password(guest, "guest1234")


def test_do_reset_password_invalid_token(client, db_session, guest, password_reset_request):

    response = do_reset_password(client, "not-a-valid-token")

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text

    db_session.expire_all()

    assert is_password(guest, "guest1234")
    assert password_reset_request.request_consumed_at is None


def test_do_reset_password_login_token_rejected(client, db_session, guest, password_reset_request):

    response = do_reset_password(client, AuthTokenHandler(user_id=guest.id).generate_auth_token())

    assert response.status_code == 400
    assert LINK_EXPIRED_TITLE in response.text

    db_session.expire_all()

    assert is_password(guest, "guest1234")


def test_do_reset_password_missing_fields(client, password_reset_request):

    response = client.post(path, data={"token": build_reset_token(password_reset_request)})

    assert response.status_code == 422
