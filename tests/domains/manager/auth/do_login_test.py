from domains.manager.enums import ManagerErrorMessage
from tests.domains.manager.auth.do_sign_up_test import do_encrypt_data

path = "/test/api/v1/manager/auth/login"


def test_do_login(client, manager):
    encrypted_data = do_encrypt_data({"email": manager.email_address, "password": "manager1234"})

    response = client.post(path, json={"data": encrypted_data})
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["email_address"] == manager.email_address
    assert response_body["manager_id"] == manager.id
    assert response_body["token"] is not None


def test_do_login_email_not_exist(client):
    encrypted_data = do_encrypt_data({"email": "not_exist@gmail.com", "password": "notExist1234"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_NOT_EXISTS.name


def test_do_login_unverified(client, unverified_manager):
    encrypted_data = do_encrypt_data({"email": unverified_manager.email_address, "password": "unverified1234"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_NOT_VERIFIED.name


def test_do_login_invalid_credentials(client, manager):
    encrypted_data = do_encrypt_data({"email": manager.email_address, "password": "wrong-password"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.INVALID_CREDENTIALS.name


def test_guest_cannot_login_as_manager(client, guest):
    encrypted_data = do_encrypt_data({"email": guest.email_address, "password": "guest1234"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_NOT_EXISTS.name
