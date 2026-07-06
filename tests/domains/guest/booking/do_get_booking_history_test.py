from core.models.booking import BookingStatusEnum
from core.services.http_request_helper import HTTPRequestHelper

path = "/test/api/v1/guest/bookings"


def test_do_get_booking_history(client, booking, resort, guest):

    request = HTTPRequestHelper(
        query_string_parameters={
            "status": BookingStatusEnum.PENDING,
        }
    ).create_request(guest)

    response = client.get(path, headers=request.headers, params=request.query_string_parameters)
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["bookings"][0]["resort_name"] == resort.name
