def test_do_get_resorts(
    client,
    fake_organization,
    resort,
    resort_review,
):

    path = "/test/api/v1/guest/resorts"

    response = client.get(path)

    response_body = response.json()

    assert response.status_code == 200
    assert response_body["resorts"][0]["address"] == resort.address
    assert response_body["resorts"][0]["base_price_per_night"] == str(resort.base_price_per_night)
    assert response_body["resorts"][0]["overall_rating"] > 0


def test_do_get_resorts_without_reviews(client, resort):
    """
    A resort nobody has reviewed yet must still be listed, with a rating of 0.
    """

    path = "/test/api/v1/guest/resorts"

    response = client.get(path)

    response_body = response.json()

    assert response.status_code == 200
    assert response_body["resorts"][0]["id"] == resort.id
    assert response_body["resorts"][0]["overall_rating"] == 0.0
