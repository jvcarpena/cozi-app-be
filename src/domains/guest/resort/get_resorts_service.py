from decimal import Decimal
from typing import Sequence

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.models.resort import ResortStatusEnum, Resort


class ResortDTO(BaseModel):
    id: int
    organization_id: int
    name: str
    base_price_per_night: Decimal
    currency: str
    address: str
    overall_rating: float


class GetResortsResponseDTO(BaseModel):
    resorts: list[ResortDTO]


def get_resorts(session: Session):

    resorts: Sequence[Resort] = session.scalars(
        select(Resort)
        .options(selectinload(Resort.reviews))
        .where(Resort.status == ResortStatusEnum.ACTIVE)
        .order_by(Resort.created_at.desc())
    ).all()

    resort_dto: list[ResortDTO] = []

    for resort in resorts:
        total_review = len(resort.reviews)
        resort_dto.append(
            ResortDTO(
                id=resort.id,
                organization_id=resort.organization_id,
                name=resort.name,
                base_price_per_night=resort.base_price_per_night,
                currency=resort.currency,
                address=resort.address,
                overall_rating=sum(r.overall_rating for r in resort.reviews) / total_review,
            )
        )

    return GetResortsResponseDTO(resorts=resort_dto)
