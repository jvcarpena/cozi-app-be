def test_do_get_resort_reviews(client, resort_review, guest):

    path = f"/test/api/v1/guest/resorts/{resort_review.resort_id}/reviews"

    response = client.get(path)

    response_body = response.json()

    assert response.status_code == 200
    assert response_body["reviews"][0]["guest_name"] == guest.first_name
