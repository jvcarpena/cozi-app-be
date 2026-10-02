from core.services.auth_token_handler import AuthTokenHandler

path = "/test/api/v1/manager/auth/logout"


def test_do_logout(client, manager):

    response = client.post(path, headers={"Authorization": AuthTokenHandler(user_id=manager.id).generate_auth_token()})

    assert response.status_code == 200


def test_do_logout_without_auth(client):

    response = client.post(path)

    assert response.status_code == 401


def test_do_logout_with_guest_token(client, guest):

    response = client.post(path, headers={"Authorization": AuthTokenHandler(user_id=guest.id).generate_auth_token()})

    assert response.status_code == 401
