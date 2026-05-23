from domains.guest.enums import GuestErrorMessage


def test_do_get_resort_details(
    client,
    resort,
    fake_organization,
    resort_review,
    resort_amenities_dining,
    resort_amenities_pool,
    resort_amenities_utility,
    resort_amenities_entertainment,
):

    path = f"/test/api/v1/guest/resorts/{resort.id}"

    response = client.get(path)

    response_body = response.json()

    assert response.status_code == 200
    assert response_body["data"]["address"] == resort.address
    assert response_body["data"]["description"] == resort.description
    assert len(response_body["data"]["amenities"]) > 0


def test_do_get_resort_details_invalid_id(client):

    path = "/test/api/v1/guest/resorts/67"

    response = client.get(path)

    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.RESORT_DOES_NOT_EXIST.name
