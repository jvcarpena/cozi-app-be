path = "/test/api/v1/guest/auth/verification"


def test_do_get_verification_page(client):

    response = client.get(path, params={"d": "fake-verification-token"})

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Verify My Account" in response.text
    assert "<title>Verify Your Account - Cozi</title>" in response.text


def test_do_get_verification_page_422(client):

    response = client.get(path)

    assert response.status_code == 422
