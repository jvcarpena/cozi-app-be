from datetime import datetime, timezone

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

    # A MASTER GETS THE ORGANIZATION, NOT A RESORT

    assert response_body["role"] == "master"
    assert response_body["organization_id"] == manager.organization_id
    assert response_body["organization_name"] == manager.organization.name
    assert response_body["resort_id"] is None


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


def test_do_login_admin(client, admin):
    encrypted_data = do_encrypt_data({"email": admin.email_address, "password": "admin1234"})

    response = client.post(path, json={"data": encrypted_data})
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["manager_id"] == admin.id
    assert response_body["token"] is not None

    # AN ADMIN GETS THE RESORT THEY MANAGE, NOT AN ORGANIZATION

    assert response_body["role"] == "admin"
    assert response_body["resort_id"] == admin.resort_id
    assert response_body["organization_id"] is None
    assert response_body["organization_name"] is None


def test_do_login_invited_admin_not_verified(client, invited_admin):
    encrypted_data = do_encrypt_data({"email": invited_admin.email_address, "password": "anything1234"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_NOT_VERIFIED.name


def test_do_login_admin_without_a_password(client, db_session, invited_admin):
    """
    An admin that has no password yet must get a clean error, not a crash while the password is checked.
    """

    invited_admin.verification.verified_at = datetime.now(tz=timezone.utc)

    db_session.commit()

    encrypted_data = do_encrypt_data({"email": invited_admin.email_address, "password": "anything1234"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.INVALID_CREDENTIALS.name


def test_do_login_removed_admin(client, deleted_admin):
    encrypted_data = do_encrypt_data({"email": deleted_admin.email_address, "password": "deleted1234"})

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_NOT_EXISTS.name
