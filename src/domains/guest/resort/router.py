from typing import Annotated

from fastapi import APIRouter, Path, Body

from core.services.auto_session import AutoSession
from domains.guest.resort.create_resort_review_service import CreateResortReviewRequestDTO, create_resort_review
from domains.guest.resort.get_resort_details_service import get_resort_details, GetResortDetailsResponseDTO
from domains.guest.resort.get_resort_reviews_service import get_resort_reviews, GetResortReviewsResponseDTO
from domains.guest.resort.get_resorts_service import get_resorts, GetResortsResponseDTO

resort_router = APIRouter(prefix="/resorts")


@resort_router.get("")
def do_get_resorts(session: AutoSession) -> GetResortsResponseDTO:

    return get_resorts(session)


@resort_router.get("/{resort_id}")
def do_get_resort_details(resort_id: Annotated[int, Path(...)], session: AutoSession) -> GetResortDetailsResponseDTO:

    return get_resort_details(resort_id, session)


@resort_router.get("/{resort_id}/reviews")
def do_get_resort_reviews(resort_id: Annotated[int, Path(...)], session: AutoSession) -> GetResortReviewsResponseDTO:

    return get_resort_reviews(resort_id, session)


@resort_router.post("/{resort_id}/reviews")
def do_create_resort_review(request_dto: Annotated[CreateResortReviewRequestDTO, Body()], session: AutoSession):

    return create_resort_review(request_dto, session)
