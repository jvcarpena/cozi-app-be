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


def test_do_logout_with_admin_token(client, admin):

    response = client.post(path, headers={"Authorization": AuthTokenHandler(user_id=admin.id).generate_auth_token()})

    assert response.status_code == 200


def test_do_logout_with_removed_admin_token(client, deleted_admin):
    """
    A token stays valid for days after it was issued, so a removed admin must be refused even with a good token.
    """

    response = client.post(
        path, headers={"Authorization": AuthTokenHandler(user_id=deleted_admin.id).generate_auth_token()}
    )

    assert response.status_code == 401
