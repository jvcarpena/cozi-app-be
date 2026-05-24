from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from core.models.resort_review import ResortReview
from domains.guest.enums import GuestErrorMessage


def test_create_resort_review(client, container_engine, resort, guest):
    path = f"/test/api/v1/guest/resorts/{resort.id}/reviews"

    request_payload = {
        "resort_id": resort.id,
        "guest_id": guest.id,
        "overall_rating": 4,
        "cleanliness_rating": 4,
        "value_rating": 4,
        "comment": f"TEST_COMMENT_RESORT_{resort.name}",
    }

    response = client.post(path, json=request_payload)

    assert response.status_code == 200

    with Session(container_engine) as session:
        review = session.scalars(
            select(ResortReview).where(
                and_(
                    ResortReview.resort_id == resort.id,
                    ResortReview.guest_id == guest.id,
                )
            )
        ).one()

        assert review.comment == f"TEST_COMMENT_RESORT_{resort.name}"
        assert review.overall_rating == 4
        assert review.value_rating == 4
        assert review.cleanliness_rating == 4


def test_create_resort_review_invalid_resort_id(client, guest):
    path = "/test/api/v1/guest/resorts/44/reviews"

    request_payload = {
        "resort_id": 44,
        "guest_id": guest.id,
        "overall_rating": 4,
        "cleanliness_rating": 4,
        "value_rating": 4,
        "comment": "INVALID_RESORT_ID",
    }

    response = client.post(path, json=request_payload)

    response_body = response.json()

    assert response.status_code == 400
    assert response_body["detail"] == GuestErrorMessage.RESORT_DOES_NOT_EXIST.name
