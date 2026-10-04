from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal, Optional

from fastapi import Path, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy import select

from core.models.resort import Resort
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from domains.manager.enums import ManagerErrorMessage


@dataclass
class UpdateResortPricingContext:
    user: AutoMasterUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated["UpdateResortPricingRequestDTO", Body()]


class UpdateResortPricingRequestDTO(BaseModel):
    base_price_per_night: Decimal = Field(gt=0, max_digits=12)
    base_price_per_day_use: Decimal = Field(gt=0, max_digits=12)
    currency: Literal["PHP"]


def update_resort_pricing(context: UpdateResortPricingContext):

    resort = context.session.scalars(select(Resort).where(Resort.id == context.resort_id)).one_or_none()

    if not resort:
        raise HTTPException(status_code=404, detail=ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name)

    if resort.organization_id != context.user.organization_id:
        raise HTTPException(status_code=403, detail=ManagerErrorMessage.NOT_YOUR_RESORT.name)

    for field, value in context.request_dto.model_dump().items():
        setattr(Resort, field, value)

    context.session.commit()

    return
