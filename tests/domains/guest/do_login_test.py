from domains.guest.enums import GuestErrorMessage
from tests.domains.guest.do_sign_up_test import do_encrypt_data

path = "/test/api/v1/guest/login"


def test_do_login(client, guest):
    encrypted_data = do_encrypt_data(
        {
            "email": guest.email_address,
            "password": "guest1234",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["email_address"] == guest.email_address
    assert response_body["guest_id"] == guest.id
    assert response_body["token"] is not None


def test_do_login_email_not_exist(client):
    encrypted_data = do_encrypt_data(
        {
            "email": "not_exist@gmail.com",
            "password": "notExist1234",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.EMAIL_NOT_EXISTS.name


def test_do_login_unverified(client, unverified_guest):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_guest.email_address,
            "password": "unverified1234",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.EMAIL_NOT_VERIFIED.name


def test_do_login_invalid_credentials(client, guest):
    encrypted_data = do_encrypt_data(
        {
            "email": guest.email_address,
            "password": "invalid1234",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.INVALID_CREDENTIALS.name
