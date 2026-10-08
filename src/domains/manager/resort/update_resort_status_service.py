from dataclasses import dataclass
from typing import Annotated

from fastapi import Path, Body, HTTPException
from pydantic import BaseModel, ConfigDict

from core.models.resort import ResortStatusEnum
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.manager.enums import ManagerErrorMessage
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.get_managed_resort import get_managed_resort
from domains.manager.resort.services.has_upcoming_bookings import has_upcoming_bookings


class UpdateResortStatusRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ResortStatusEnum


@dataclass
class UpdateResortStatusContext:
    user: AutoManagerUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated[UpdateResortStatusRequestDTO, Body()]


def update_resort_status(context: UpdateResortStatusContext) -> GetResortDetailResponseDTO:

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    new_status = context.request_dto.status

    # A LIVE RESORT CANNOT BE CLOSED (INACTIVE OR MAINTENANCE) WHILE GUESTS STILL HAVE BOOKINGS AT IT.
    # THE BOOKINGS HAVE TO BE CANCELLED OR FINISHED FIRST.

    if (
        resort.status == ResortStatusEnum.ACTIVE
        and new_status != ResortStatusEnum.ACTIVE
        and has_upcoming_bookings(context.session, resort.id)
    ):

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.RESORT_HAS_UPCOMING_BOOKINGS.name)

    resort.status = new_status

    context.session.commit()

    return build_resort_detail(context.session, context.user, resort)
