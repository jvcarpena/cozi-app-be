from typing import Optional, List, Annotated
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Path
from pydantic import BaseModel, AwareDatetime
from sqlalchemy import and_, exists, select
from sqlalchemy.orm import Session, selectinload

from core.models.resort import Resort, ResortStatusEnum
from core.models.resort_review import ResortReview
from domains.guest.enums import GuestErrorMessage


class ResortReviewDTO(BaseModel):
    id: int
    guest_name: str
    overall_rating: int
    cleanliness_rating: int
    value_rating: int
    comment: Optional[str] = None
    created_at: AwareDatetime


class GetResortReviewsResponseDTO(BaseModel):
    reviews: List[ResortReviewDTO]


def get_resort_reviews(resort_id: Annotated[int, Path(...)], session: Session) -> GetResortReviewsResponseDTO:

    # A RESORT THAT DOES NOT EXIST AND A DRAFT (INACTIVE) RESORT GET THE SAME ANSWER, SO DRAFTS CANNOT BE FOUND

    resort_is_visible = session.scalars(
        select(exists().where(and_(Resort.id == resort_id, Resort.status != ResortStatusEnum.INACTIVE)))
    ).one()

    if not resort_is_visible:
        raise HTTPException(status_code=404, detail=GuestErrorMessage.RESORT_DOES_NOT_EXIST.name)

    reviews = session.scalars(
        select(ResortReview)
        .options(selectinload(ResortReview.guest))
        .where(
            ResortReview.resort_id == resort_id,
        )
    ).all()

    reviews_dto = [
        ResortReviewDTO(
            id=r.id,
            guest_name=r.guest.first_name,
            overall_rating=r.overall_rating,
            cleanliness_rating=r.cleanliness_rating,
            value_rating=r.value_rating,
            comment=r.comment,
            created_at=r.created_at.astimezone(ZoneInfo("Asia/Manila")),
        )
        for r in reviews
    ]

    return GetResortReviewsResponseDTO(reviews=reviews_dto)
