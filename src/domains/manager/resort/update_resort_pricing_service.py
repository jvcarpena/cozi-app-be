from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import Path, Body
from pydantic import BaseModel, ConfigDict

from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.get_managed_resort import get_managed_resort
from domains.manager.resort.services.resort_field_types import ResortPrice


class UpdateResortPricingRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base_price_per_night: ResortPrice
    base_price_per_day_use: ResortPrice
    currency: Literal["PHP"]


@dataclass
class UpdateResortPricingContext:
    user: AutoMasterUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated[UpdateResortPricingRequestDTO, Body()]


def update_resort_pricing(context: UpdateResortPricingContext) -> GetResortDetailResponseDTO:
    """
    Only a master can change prices. Bookings that were already made keep the price they were made with.
    """

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    resort.base_price_per_night = context.request_dto.base_price_per_night

    resort.base_price_per_day_use = context.request_dto.base_price_per_day_use

    resort.currency = context.request_dto.currency

    context.session.commit()

    return build_resort_detail(context.session, context.user, resort)
