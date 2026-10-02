import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.manager.enums import ManagerErrorMessage

path = "/test/api/v1/manager/auth/signup"


def do_encrypt_data(data: dict) -> str:

    return SecurePayloadHandler(data_to_encrypt=data).encrypt_payload().data


@pytest.mark.usefixtures("celery_worker")
def test_do_sign_up(client, db_session, container_engine):
    encrypted_data = do_encrypt_data(
        {
            "email": "test_email@gmail.com",
            "first_name": "test",
            "last_name": "name",
            "password": "test1234",
            "phone": "",
        }
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 200

    with Session(container_engine) as session:
        user = session.scalars(select(Admin).where(Admin.email_address == "test_email@gmail.com")).one()

        assert user is not None
        assert user.verification.verified_at is None


def test_do_sign_up_email_registered(client, manager):
    encrypted_data = do_encrypt_data(
        {
            "email": manager.email_address,
            "first_name": manager.first_name,
            "last_name": manager.last_name,
            "password": "manager1234",
            "phone": "",
        }
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_REGISTERED.name


def test_do_sign_up_check_your_email(client, unverified_manager):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_manager.email_address,
            "first_name": unverified_manager.first_name,
            "last_name": unverified_manager.last_name,
            "password": "unverified1234",
            "phone": "",
        }
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.CHECK_YOUR_EMAIL.name


@pytest.mark.usefixtures("celery_worker")
def test_do_sign_up_unverified_manager_expired_link(client, unverified_manager_expired_link):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_manager_expired_link.email_address,
            "first_name": unverified_manager_expired_link.first_name,
            "last_name": unverified_manager_expired_link.last_name,
            "password": "linkexpired1234",
            "phone": "",
        }
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 200
