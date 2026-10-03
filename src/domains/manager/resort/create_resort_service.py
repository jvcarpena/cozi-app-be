from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Annotated, Literal

from fastapi import Body, HTTPException
from pydantic import BaseModel, StringConstraints, Field
from sqlalchemy import exists, select

from core.models.resort import Resort, ResortStatusEnum
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from domains.manager.enums import ManagerErrorMessage


class CreateResortRequestDTO(BaseModel):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
    description: str
    base_price_per_night: Decimal = Field(gt=0, max_digits=12)
    base_price_per_day_use: Decimal = Field(gt=0, max_digits=12)
    currency: Literal["PHP"]
    max_guests: int = Field(gt=0)
    num_bedrooms: int = Field(gt=0)
    num_bathrooms: int = Field(gt=0)
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: str


@dataclass
class CreateResortContext:
    user: AutoMasterUser
    session: AutoSession
    request_dto: Annotated[CreateResortRequestDTO, Body()]


def create_resort(context: CreateResortContext):

    if context.session.scalars(select(exists().where(Resort.name == context.request_dto.name))).one_or_none():

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name)

    context.session.add(
        Resort(
            organization_id=context.user.organization_id,
            name=context.request_dto.name,
            status=ResortStatusEnum.INACTIVE,
            description=context.request_dto.description,
            base_price_per_night=context.request_dto.base_price_per_night,
            base_price_per_day_use=context.request_dto.base_price_per_day_use,
            currency=context.request_dto.currency,
            max_guests=context.request_dto.max_guests,
            num_bedrooms=context.request_dto.num_bedrooms,
            num_bathrooms=context.request_dto.num_bathrooms,
            latitude=context.request_dto.latitude,
            longitude=context.request_dto.longitude,
            address=context.request_dto.address,
        )
    )

    context.session.commit()

    return
