from dataclasses import dataclass, Field
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import Path, Body, HTTPException
from pydantic import BaseModel, StringConstraints
from sqlalchemy import select

from core.models.admin import Admin
from core.models.master import Master
from core.models.resort import Resort
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.manager.enums import ManagerErrorMessage


@dataclass
class UpdateResortDetailContext:
    user: AutoManagerUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated["UpdateResortRequestDTO", Body()]


class UpdateResortRequestDTO(BaseModel):
    name: Optional[Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]] = None
    description: Optional[str] = None
    max_guests: Optional[int] = None
    num_bedrooms: Optional[int] = None
    num_bathrooms: Optional[int] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: Optional[str] = None


def update_resort_detail(context: UpdateResortDetailContext):

    resort: Resort = context.session.scalars(select(Resort).where(Resort.id == context.resort_id)).one_or_none()

    if not resort:
        raise HTTPException(status_code=404, detail=ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name)

    if isinstance(context.user, Master) and resort.organization_id != context.user.organization_id:
        raise HTTPException(status_code=403, detail=ManagerErrorMessage.NOT_YOUR_RESORT.name)

    if isinstance(context.user, Admin) and resort.id != context.user.resort_id:
        raise HTTPException(status_code=403, detail=ManagerErrorMessage.NOT_YOUR_RESORT.name)

    for field, value in context.request_dto.model_dump(exclude_none=True):
        setattr(resort, field, value)

    context.session.commit()

    return
