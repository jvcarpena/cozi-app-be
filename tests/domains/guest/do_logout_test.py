from core.services.auth_token_handler import AuthTokenHandler

path = "/test/api/v1/guest/logout"


def test_do_logout(client, guest):

    response = client.post(
        path,
        headers={
            "Authorization": AuthTokenHandler(user_id=guest.id).generate_auth_token(),
        },
    )

    assert response.status_code == 200


def test_do_logout_without_auth(client):
    """
    FastAPI throws 401 error if auth is not included in headers.

    :param client:
    :return: 401
    """

    response = client.post(path)

    assert response.status_code == 401
