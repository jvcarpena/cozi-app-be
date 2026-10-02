from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.auth.do_sign_up_test import do_encrypt_data

path = "/test/api/v1/manager/auth/verify"


def test_get_verification_page(client):
    response = client.get(path, params={"d": "some-token"})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert 'action="/manager/auth/verify"' in response.text


def test_verify_manager(client, unverified_manager):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_manager.email_address,
            "first_name": unverified_manager.first_name,
            "last_name": unverified_manager.last_name,
            "password": "unverified1234",
            "phone": "",
        }
    )

    response = client.post(path, data={"data": encrypted_data})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "<title>Account Verified - Cozi</title>" in response.text


def test_verify_manager_not_exist(client):
    encrypted_data = do_encrypt_data(
        {
            "email": "not_exist@gmail.com",
            "first_name": "Manager",
            "last_name": "NotExist",
            "password": "NotExist1234",
            "phone": "",
        }
    )

    response = client.post(path, data={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.ACCOUNT_DOES_NOT_EXISTS.name


def test_verify_manager_link_expired(client, unverified_manager_expired_link):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_manager_expired_link.email_address,
            "first_name": unverified_manager_expired_link.first_name,
            "last_name": unverified_manager_expired_link.last_name,
            "password": "linkexpired1234",
            "phone": "",
        }
    )

    response = client.post(path, data={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.LINK_EXPIRED.name
