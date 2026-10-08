from core.services.http_request_helper import HTTPRequestHelper

BASE_PATH = "/test/api/v1/manager/resorts"


def call(client, method: str, path: str, user=None, json=None):
    """
    Sends a request as the user (a master, an admin or a guest). Without a user there is no Authorization header.
    """

    headers = HTTPRequestHelper().create_request(user).headers if user is not None else {}

    return client.request(method, path, headers=headers, json=json)


def resort_payload(**overrides) -> dict:
    """
    A valid create resort payload. Pass a field to replace it, or set a field to None to leave it out.
    """

    payload = {
        "name": "Sunrise Resort",
        "description": "Beachfront resort with a private pool.",
        "base_price_per_night": "25000.50",
        "base_price_per_day_use": "12000",
        "currency": "PHP",
        "max_guests": 20,
        "num_bedrooms": 4,
        "num_bathrooms": 3,
        "address": "Pansol, Calamba, Laguna",
    }

    payload.update(overrides)

    return {key: value for key, value in payload.items() if value is not None}
