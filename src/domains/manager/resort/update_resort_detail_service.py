from dataclasses import dataclass
from typing import Annotated, Optional

from fastapi import Path, Body
from pydantic import BaseModel, ConfigDict, model_validator

from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.check_resort_name import check_resort_name_is_free, commit_resort
from domains.manager.resort.services.get_managed_resort import get_managed_resort
from domains.manager.resort.services.resort_field_types import (
    Latitude,
    Longitude,
    ResortAddress,
    ResortDescription,
    ResortMaxGuests,
    ResortName,
    ResortRoomCount,
)

# THE ONLY FIELDS THAT CAN BE SENT AS NULL, TO REMOVE THE COORDINATES OF THE RESORT.
NULLABLE_FIELDS = {"latitude", "longitude"}


class UpdateResortRequestDTO(BaseModel):

    # PRICES AND THE STATUS HAVE THEIR OWN ENDPOINTS. A FIELD THAT IS NOT LISTED HERE IS REJECTED (422)
    # INSTEAD OF BEING SILENTLY IGNORED, SO A CLIENT NEVER THINKS A PRICE WAS CHANGED WHEN IT WAS NOT.

    model_config = ConfigDict(extra="forbid")

    name: Optional[ResortName] = None
    description: Optional[ResortDescription] = None
    max_guests: Optional[ResortMaxGuests] = None
    num_bedrooms: Optional[ResortRoomCount] = None
    num_bathrooms: Optional[ResortRoomCount] = None
    latitude: Optional[Latitude] = None
    longitude: Optional[Longitude] = None
    address: Optional[ResortAddress] = None

    @model_validator(mode="after")
    def validate_fields_sent(self) -> "UpdateResortRequestDTO":

        if not self.model_fields_set:

            raise ValueError("send at least one field to change")

        for field in self.model_fields_set - NULLABLE_FIELDS:

            if getattr(self, field) is None:

                raise ValueError(f"{field} cannot be null")

        # THE COORDINATES ARE A PAIR: SENT TOGETHER, AND EITHER BOTH SET OR BOTH REMOVED.

        if ("latitude" in self.model_fields_set) != ("longitude" in self.model_fields_set):

            raise ValueError("latitude and longitude must be sent together")

        if (self.latitude is None) != (self.longitude is None):

            raise ValueError("latitude and longitude must both have a value or both be null")

        return self


@dataclass
class UpdateResortDetailContext:
    user: AutoManagerUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated[UpdateResortRequestDTO, Body()]


def update_resort_detail(context: UpdateResortDetailContext) -> GetResortDetailResponseDTO:

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    # RENAMING TO THE NAME THE RESORT ALREADY HAS IS NOT A CLASH

    if "name" in context.request_dto.model_fields_set:

        check_resort_name_is_free(
            context.session, resort.organization_id, context.request_dto.name, exclude_resort_id=resort.id
        )

    # ONLY THE FIELDS THE CLIENT SENT ARE CHANGED

    for field in context.request_dto.model_fields_set:

        setattr(resort, field, getattr(context.request_dto, field))

    commit_resort(context.session)

    return build_resort_detail(context.session, context.user, resort)
