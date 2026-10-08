import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.resort import ResortStatusEnum
from core.models.resort_review import ResortReview
from core.services.http_request_helper import HTTPRequestHelper
from domains.guest.enums import GuestErrorMessage

# A MANAGER CREATES A RESORT AS A DRAFT (INACTIVE) AND ACTIVATES IT WHEN IT IS READY.
# WHAT A GUEST CAN SEE AND DO DEPENDS ON THAT STATUS:
#
#   ACTIVE       listed, visible, reviewable
#   MAINTENANCE  not listed, but the page and the reviews can still be opened
#   INACTIVE     a draft: not listed, and its page and reviews answer like a resort that does not exist

VISIBLE_STATUSES = [ResortStatusEnum.ACTIVE, ResortStatusEnum.MAINTENANCE]

path = "/test/api/v1/guest/resorts"


def set_status(db_session, resort, status: ResortStatusEnum):

    resort.status = status

    db_session.commit()


def review_body(resort) -> dict:

    return {
        "resort_id": resort.id,
        "overall_rating": 4,
        "cleanliness_rating": 4,
        "value_rating": 4,
        "comment": "VISIBILITY TEST",
    }


# LIST


@pytest.mark.parametrize("status", [ResortStatusEnum.INACTIVE, ResortStatusEnum.MAINTENANCE])
def test_list_only_shows_active_resorts(client, db_session, resort, status):

    set_status(db_session, resort, status)

    response = client.get(path)

    assert response.status_code == 200
    assert response.json() == {"resorts": []}


def test_list_shows_an_active_resort_without_reviews(client, resort):
    """
    A resort nobody has reviewed yet, like a resort a manager just activated.
    """

    response = client.get(path)

    assert response.status_code == 200
    assert [item["id"] for item in response.json()["resorts"]] == [resort.id]


# DETAILS


@pytest.mark.parametrize("status", VISIBLE_STATUSES)
def test_details_visible_resort(client, db_session, resort, status):

    set_status(db_session, resort, status)

    response = client.get(f"{path}/{resort.id}")

    assert response.status_code == 200
    assert response.json()["data"]["id"] == resort.id


def test_details_draft_resort_is_not_found(client, db_session, resort):

    set_status(db_session, resort, ResortStatusEnum.INACTIVE)

    response = client.get(f"{path}/{resort.id}")

    assert response.status_code == 404
    assert response.json()["detail"] == GuestErrorMessage.RESORT_DOES_NOT_EXIST.name


def test_details_draft_looks_the_same_as_a_missing_resort(client, db_session, resort):

    set_status(db_session, resort, ResortStatusEnum.INACTIVE)

    draft = client.get(f"{path}/{resort.id}")
    missing = client.get(f"{path}/999999")

    assert draft.status_code == missing.status_code == 404
    assert draft.json() == missing.json()


# REVIEWS


@pytest.mark.parametrize("status", VISIBLE_STATUSES)
def test_reviews_of_a_visible_resort(client, db_session, resort, status):

    set_status(db_session, resort, status)

    response = client.get(f"{path}/{resort.id}/reviews")

    assert response.status_code == 200
    assert response.json() == {"reviews": []}


def test_reviews_of_a_draft_resort_are_not_found(client, db_session, resort):

    set_status(db_session, resort, ResortStatusEnum.INACTIVE)

    response = client.get(f"{path}/{resort.id}/reviews")

    assert response.status_code == 404
    assert response.json()["detail"] == GuestErrorMessage.RESORT_DOES_NOT_EXIST.name


def test_reviews_of_an_unknown_resort_are_not_found(client):

    response = client.get(f"{path}/999999/reviews")

    assert response.status_code == 404
    assert response.json()["detail"] == GuestErrorMessage.RESORT_DOES_NOT_EXIST.name


# POSTING A REVIEW


@pytest.mark.parametrize("status", VISIBLE_STATUSES)
def test_review_can_be_posted_on_a_visible_resort(client, container_engine, db_session, resort, guest, status):

    set_status(db_session, resort, status)

    request = HTTPRequestHelper(body=review_body(resort)).create_request(guest)

    response = client.post(f"{path}/{resort.id}/reviews", headers=request.headers, json=request.body)

    assert response.status_code == 200

    with Session(container_engine) as session:
        assert len(session.scalars(select(ResortReview)).all()) == 1


def test_review_cannot_be_posted_on_a_draft_resort(client, container_engine, db_session, resort, guest):

    set_status(db_session, resort, ResortStatusEnum.INACTIVE)

    request = HTTPRequestHelper(body=review_body(resort)).create_request(guest)

    response = client.post(f"{path}/{resort.id}/reviews", headers=request.headers, json=request.body)

    assert response.status_code == 404
    assert response.json()["detail"] == GuestErrorMessage.RESORT_DOES_NOT_EXIST.name

    with Session(container_engine) as session:
        assert session.scalars(select(ResortReview)).all() == []
