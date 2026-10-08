from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select, exists
from sqlalchemy.orm import Session

from core.models.guest import Guest
from core.models.resort import Resort, ResortStatusEnum
from core.models.resort_review import ResortReview
from domains.guest.enums import GuestErrorMessage


class CreateResortReviewRequestDTO(BaseModel):
    resort_id: int
    overall_rating: int
    cleanliness_rating: int
    value_rating: int
    comment: Optional[str] = None


def create_resort_review(request_dto: CreateResortReviewRequestDTO, session: Session, guest: Guest):

    # CHECK FIRST IF RESORT EXIST.

    resort = session.scalars(
        select(
            exists().where(
                Resort.id == request_dto.resort_id,
                Resort.status != ResortStatusEnum.INACTIVE,
            )
        )
    ).one_or_none()

    if not resort:
        raise HTTPException(status_code=404, detail=GuestErrorMessage.RESORT_DOES_NOT_EXIST.name)

    session.add(
        ResortReview(
            resort_id=request_dto.resort_id,
            guest_id=guest.id,
            overall_rating=request_dto.overall_rating,
            cleanliness_rating=request_dto.cleanliness_rating,
            value_rating=request_dto.value_rating,
            comment=request_dto.comment,
        )
    )

    session.commit()

    return
