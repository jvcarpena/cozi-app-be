from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.guest import Guest
from core.services.secure_payload_handler import SecurePayloadHandler
from domains.guest.enums import GuestErrorMessage

path = "/test/api/v1/guest/sign-up"


def do_encrypt_data(data: dict) -> str:

    return SecurePayloadHandler(data_to_encrypt=data).encrypt_payload().data


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

    response = client.post(
        path,
        json={"data": encrypted_data},
    )

    assert response.status_code == 200

    with Session(container_engine) as session:

        user = session.scalars(select(Guest).where(Guest.email_address == "test_email@gmail.com")).one()

        assert user is not None


def test_do_sign_up_email_registered(client, guest):
    encrypted_data = do_encrypt_data(
        {
            "email": guest.email_address,
            "first_name": guest.first_name,
            "last_name": guest.last_name,
            "password": "guest1234",
            "phone": "",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.EMAIL_REGISTERED.name


def test_do_sign_up_check_your_email(client, unverified_guest):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_guest.email_address,
            "first_name": unverified_guest.first_name,
            "last_name": unverified_guest.last_name,
            "password": "unverified1234",
            "phone": "",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.CHECK_YOUR_EMAIL.name


def test_do_sign_up_unverified_guest_expired_link(client, unverified_guest_expired_link):
    encrypted_data = do_encrypt_data(
        {
            "email": unverified_guest_expired_link.email_address,
            "first_name": unverified_guest_expired_link.first_name,
            "last_name": unverified_guest_expired_link.last_name,
            "password": "linkexpired1234",
            "phone": "",
        }
    )

    response = client.post(
        path,
        json={"data": encrypted_data},
    )

    assert response.status_code == 200
