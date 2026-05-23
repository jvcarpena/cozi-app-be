from decimal import Decimal
from itertools import groupby
from typing import Annotated, Optional

from fastapi import Path, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from core.models.resort import ResortStatusEnum, Resort
from core.models.resort_amenity import ResortAmenityCategoryEnum
from core.models.resort_review import ResortReview
from domains.guest.enums import GuestErrorMessage


class ResortDTO(BaseModel):
    id: int
    organization_id: int
    name: str
    status: ResortStatusEnum
    description: str
    base_price_per_night: Decimal
    currency: str
    max_guests: int
    num_bedrooms: int
    num_bathrooms: int
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: str
    amenities: list["ResortAmenityDTO"]
    ratings: "ResortRatingDTO"


class ResortAmenityDTO(BaseModel):
    category: ResortAmenityCategoryEnum
    names: list[str]


class ResortRatingDTO(BaseModel):
    overall: float
    cleanliness: float
    value: float
    total_reviews: int


class GetResortDetailsResponseDTO(BaseModel):
    data: ResortDTO


def get_resort_details(resort_id: Annotated[int, Path(...)], session: Session):

    resort: Resort = session.scalars(
        select(Resort)
        .options(
            selectinload(Resort.amenities),
            selectinload(Resort.reviews),
        )
        .where(
            Resort.id == resort_id,
        )
    ).one_or_none()

    if not resort:
        raise HTTPException(status_code=400, detail=GuestErrorMessage.RESORT_DOES_NOT_EXIST.name)

    def build_ratings(reviews: list[ResortReview]) -> ResortRatingDTO:
        if not reviews:
            return ResortRatingDTO(
                overall=0.0,
                cleanliness=0.0,
                value=0.0,
                total_reviews=0,
            )

        total = len(reviews)

        return ResortRatingDTO(
            overall=sum(r.overall_rating for r in reviews) / total,
            cleanliness=sum(r.cleanliness_rating for r in reviews) / total,
            value=sum(r.value_rating for r in reviews) / total,
            total_reviews=total,
        )

    grouped_amenities = [
        ResortAmenityDTO(
            category=category,
            names=[a.name for a in amenities],
        )
        for category, amenities in groupby(sorted(resort.amenities, key=lambda a: a.category), key=lambda a: a.category)
    ]

    response = ResortDTO(
        id=resort.id,
        organization_id=resort.organization_id,
        name=resort.name,
        status=resort.status,
        description=resort.description,
        base_price_per_night=resort.base_price_per_night,
        currency=resort.currency,
        max_guests=resort.max_guests,
        num_bedrooms=resort.num_bedrooms,
        num_bathrooms=resort.num_bathrooms,
        address=resort.address,
        amenities=grouped_amenities,
        ratings=build_ratings(resort.reviews),
    )

    return GetResortDetailsResponseDTO(data=response)
