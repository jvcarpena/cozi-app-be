from dataclasses import dataclass
from typing import Annotated

from fastapi import Path, Body, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, and_, or_

from core.models.admin import Admin
from core.models.master import Master
from core.models.resort import ResortStatusEnum, Resort
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.manager.enums import ManagerErrorMessage


@dataclass
class UpdateResortStatusContext:
    user: AutoManagerUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated["UpdateResortStatusRequestDTO", Body()]


class UpdateResortStatusRequestDTO(BaseModel):
    status: ResortStatusEnum


def update_resort_status(context: UpdateResortStatusContext):

    resort: Resort = context.session.scalars(
        select(Resort).where(
            and_(
                Resort.id == context.resort_id,
                Resort.deleted_at.is_(None),
            )
        )
    ).one_or_none()

    if not resort:
        raise HTTPException(status_code=404, detail=ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name)

    if isinstance(context.user, Master) and resort.organization_id != context.user.organization_id:
        raise HTTPException(status_code=403, detail=ManagerErrorMessage.NOT_YOUR_RESORT.name)

    for field, value in context.request_dto.model_dump().items():
        setattr(resort, field, value)

    context.session.commit()

    return
