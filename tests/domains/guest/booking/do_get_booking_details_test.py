from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage


def test_do_get_booking_details(client, booking, resort, guest):

    path = f"/test/api/v1/guest/bookings/{booking.id}"

    request = HTTPRequestHelper().create_request(guest)

    response = client.get(path, headers=request.headers)
    response_body = response.json()

    assert response.status_code == 200
    assert response_body["status"] == booking.status
    assert response_body["num_guests"] == booking.num_guests
    assert response_body["total_price"] == str(booking.total_price)


def test_do_get_booking_details_404(client, guest):

    path = "/test/api/v1/guest/bookings/69"

    request = HTTPRequestHelper().create_request(guest)

    response = client.get(path, headers=request.headers)
    response_body = response.json()

    assert response.status_code == 404
    assert response_body["detail"] == GuestErrorMessage.BOOKING_DOES_NOT_EXIST.name
