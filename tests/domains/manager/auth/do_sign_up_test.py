import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from ulid import ULID

from core.models.master import Master
from core.models.organization import Organization
from core.services.secure_payload_handler import PayloadError, SecurePayloadHandler
from domains.guest.enums import GuestErrorMessage
from domains.manager.enums import ManagerErrorMessage

path = "/test/api/v1/manager/auth/signup"


def do_encrypt_data(data: dict) -> str:

    return SecurePayloadHandler(data_to_encrypt=data).encrypt_payload().data


def sign_up_payload(**overrides) -> dict:
    """
    A valid manager sign up payload. Pass a field to replace it, or set a field to None to leave it out.
    """

    payload = {
        "email": "test_email@gmail.com",
        "first_name": "test",
        "last_name": "name",
        "password": "test1234",
        "phone": "",
        "organization_name": "TEST_ORGANIZATION",
    }

    payload.update(overrides)

    return {key: value for key, value in payload.items() if value is not None}


@pytest.fixture
def send_email_task_mock(mocker):
    """
    Replaces the Celery task so no broker, worker or SMTP server is needed. The test only checks what was queued.
    """

    return mocker.patch("domains.manager.auth.sign_up_service.send_email_task")


@pytest.mark.usefixtures("celery_worker")
def test_do_sign_up(client, db_session, container_engine):
    encrypted_data = do_encrypt_data(sign_up_payload())

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 200

    # EVERY MANAGER THAT SIGNS UP BECOMES A MASTER THAT OWNS A NEW ORGANIZATION

    with Session(container_engine) as session:
        user = session.scalars(select(Master).where(Master.email_address == "test_email@gmail.com")).one()

        assert user.user_type == "master"
        assert user.verification.verified_at is None
        assert len(user.id) == 26 and ULID.from_str(user.id)
        assert user.organization.name == "TEST_ORGANIZATION"


def test_do_sign_up_queues_the_verification_email(client, container_engine, send_email_task_mock):

    response = client.post(path, json={"data": do_encrypt_data(sign_up_payload())})

    assert response.status_code == 200

    send_email_task_mock.delay.assert_called_once()

    email_request = send_email_task_mock.delay.call_args.args[0]

    assert email_request["to"] == "test_email@gmail.com"
    assert "/manager/auth/verify?d=" in email_request["html_substitutions"]["verification_url"]


def test_do_sign_up_trims_the_organization_name(client, container_engine, send_email_task_mock):

    client.post(path, json={"data": do_encrypt_data(sign_up_payload(organization_name="  My Resorts  "))})

    with Session(container_engine) as session:
        assert session.scalars(select(Organization.name)).all() == ["My Resorts"]


def test_do_sign_up_email_registered(client, manager):
    encrypted_data = do_encrypt_data(
        sign_up_payload(email=manager.email_address, first_name=manager.first_name, last_name=manager.last_name)
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_REGISTERED.name


@pytest.mark.parametrize("admin_fixture", ["admin", "invited_admin"])
def test_do_sign_up_email_of_an_admin(client, request, admin_fixture, send_email_task_mock):
    """
    An admin is invited by a master, so their email can never be used to sign up as a master.
    """

    admin = request.getfixturevalue(admin_fixture)

    response = client.post(path, json={"data": do_encrypt_data(sign_up_payload(email=admin.email_address))})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.EMAIL_REGISTERED.name

    send_email_task_mock.delay.assert_not_called()


def test_do_sign_up_email_of_a_removed_admin_is_free(client, container_engine, deleted_admin, send_email_task_mock):

    response = client.post(path, json={"data": do_encrypt_data(sign_up_payload(email=deleted_admin.email_address))})

    assert response.status_code == 200

    with Session(container_engine) as session:
        assert session.scalars(select(Master).where(Master.email_address == deleted_admin.email_address)).one()


def test_do_sign_up_check_your_email(client, unverified_manager):
    encrypted_data = do_encrypt_data(
        sign_up_payload(
            email=unverified_manager.email_address,
            first_name=unverified_manager.first_name,
            last_name=unverified_manager.last_name,
            password="unverified1234",
        )
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 400
    assert response.json()["detail"] == ManagerErrorMessage.CHECK_YOUR_EMAIL.name


@pytest.mark.usefixtures("celery_worker")
def test_do_sign_up_unverified_manager_expired_link(client, container_engine, unverified_manager_expired_link):
    encrypted_data = do_encrypt_data(
        sign_up_payload(
            email=unverified_manager_expired_link.email_address,
            first_name=unverified_manager_expired_link.first_name,
            last_name=unverified_manager_expired_link.last_name,
            password="linkexpired1234",
            organization_name="CHANGED_ORGANIZATION",
        )
    )

    response = client.post(path, json={"data": encrypted_data})

    assert response.status_code == 200

    # THE DETAILS THE MANAGER SENT THIS TIME REPLACE THE OLD ONES

    with Session(container_engine) as session:
        master = session.get(Master, unverified_manager_expired_link.id)

        assert master.organization.name == "CHANGED_ORGANIZATION"

        assert len(session.scalars(select(Organization)).all()) == 1


def test_do_sign_up_password_too_short(client):
    encrypted_data = do_encrypt_data(sign_up_payload(email="short_password@gmail.com", password="12345"))

    response = client.post(
        path,
        json={"data": encrypted_data},
    )
    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.INVALID_PASSWORD_LENGTH.name


@pytest.mark.parametrize("organization_name", [None, "", "   ", "a" * 257])
def test_do_sign_up_invalid_organization_name(client, organization_name, send_email_task_mock):
    """
    The organization name is required: a missing, blank or too long name is rejected before anything is saved.
    """

    payload = sign_up_payload(organization_name=organization_name)

    response = client.post(path, json={"data": do_encrypt_data(payload)})

    assert response.status_code == 422
    assert response.json()["detail"] == PayloadError.INVALID_PAYLOAD.name

    send_email_task_mock.delay.assert_not_called()


def test_do_sign_up_payload_cannot_be_decrypted(client, send_email_task_mock):

    response = client.post(path, json={"data": "this-is-not-an-encrypted-payload"})

    assert response.status_code == 400
    assert response.json()["detail"] == PayloadError.INVALID_PAYLOAD.name

    send_email_task_mock.delay.assert_not_called()
