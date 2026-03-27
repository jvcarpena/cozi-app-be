from domains.guest.enums import GuestErrorMessage
from tests.domains.guest.do_sign_up_test import do_encrypt_data

path = "/test/api/v1/guest/verification"


def test_verify_guest(client, unverified_guest):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_guest.email_address,
            "first_name": unverified_guest.first_name,
            "last_name": unverified_guest.last_name,
            "password": "unverified1234",
            "phone": "",
        }
    )

    response = client.post(path, data={"data": encrypted_data})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Account Verified - Cozi</title>" in response.text
    assert "Your email address has been successfully verified." in response.text


def test_verify_guest_not_exist(client):
    encrypted_data = do_encrypt_data(
        {
            "email": "not_exist@gmail.com",
            "first_name": "Guest",
            "last_name": "NotExist",
            "password": "NotExist1234",
            "phone": "",
        }
    )

    response = client.post(path, data={"data": encrypted_data})
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.ACCOUNT_DOES_NOT_EXISTS.name


def test_verify_guest_link_expired(client, unverified_guest_expired_link):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_guest_expired_link.email_address,
            "first_name": unverified_guest_expired_link.first_name,
            "last_name": unverified_guest_expired_link.last_name,
            "password": "linkexpired1234",
            "phone": "",
        }
    )

    response = client.post(path, data={"data": encrypted_data})
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.LINK_EXPIRED.name
