from dataclasses import dataclass
from typing import Annotated, Literal, Optional

from fastapi import Body
from pydantic import BaseModel, ConfigDict, model_validator

from core.models.resort import Resort, ResortStatusEnum
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.check_resort_name import check_resort_name_is_free, commit_resort
from domains.manager.resort.services.resort_field_types import (
    Latitude,
    Longitude,
    ResortAddress,
    ResortDescription,
    ResortMaxGuests,
    ResortName,
    ResortPrice,
    ResortRoomCount,
)


class CreateResortRequestDTO(BaseModel):

    # THE ORGANIZATION AND THE STATUS ARE NEVER SENT BY THE CLIENT, A FIELD THAT IS NOT LISTED IS REJECTED.

    model_config = ConfigDict(extra="forbid")

    name: ResortName
    description: ResortDescription
    base_price_per_night: ResortPrice
    base_price_per_day_use: ResortPrice
    currency: Literal["PHP"]
    max_guests: ResortMaxGuests
    num_bedrooms: ResortRoomCount
    num_bathrooms: ResortRoomCount
    latitude: Optional[Latitude] = None
    longitude: Optional[Longitude] = None
    address: ResortAddress

    @model_validator(mode="after")
    def coordinates_come_together(self) -> "CreateResortRequestDTO":

        if (self.latitude is None) != (self.longitude is None):

            raise ValueError("latitude and longitude must be sent together")

        return self


@dataclass
class CreateResortContext:
    user: AutoMasterUser
    session: AutoSession
    request_dto: Annotated[CreateResortRequestDTO, Body()]


def create_resort(context: CreateResortContext) -> GetResortDetailResponseDTO:

    # A RESORT NAME IS UNIQUE INSIDE THE ORGANIZATION OF THE MASTER

    check_resort_name_is_free(context.session, context.user.organization_id, context.request_dto.name)

    # THE RESORT ALWAYS STARTS AS A DRAFT (INACTIVE) IN THE ORGANIZATION OF THE MASTER

    context.session.add(
        resort := Resort(
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

    commit_resort(context.session)

    return build_resort_detail(context.session, context.user, resort)
