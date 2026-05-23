def test_do_get_resorts(
    client,
    fake_organization,
    resort,
    resort_review,
    resort_amenities_dining,
    resort_amenities_pool,
    resort_amenities_utility,
    resort_amenities_entertainment,
):

    path = "/test/api/v1/guest/resorts"

    response = client.get(path)

    response_body = response.json()

    assert response.status_code == 200
    assert response_body["resorts"][0]["address"] == resort.address
    assert response_body["resorts"][0]["description"] == resort.description
    assert len(response_body["resorts"][0]["amenities"]) > 0
