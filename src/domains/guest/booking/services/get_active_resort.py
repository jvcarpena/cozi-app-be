from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.resort import Resort, ResortStatusEnum
from domains.guest.enums import GuestErrorMessage


def get_active_resort(session: Session, resort_id: int) -> Resort:

    resort = session.scalars(select(Resort).where(Resort.id == resort_id)).one_or_none()

    if not resort:
        raise HTTPException(status_code=400, detail=GuestErrorMessage.RESORT_DOES_NOT_EXIST.name)

    if resort.status == ResortStatusEnum.INACTIVE:
        raise HTTPException(status_code=400, detail=GuestErrorMessage.RESORT_IS_NOT_AVAILABLE.name)

    return resort
