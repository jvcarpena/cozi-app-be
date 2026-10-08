from fastapi import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.master import Master
from core.models.resort import Resort
from domains.manager.enums import ManagerErrorMessage


def get_managed_resort(session: Session, user: Master | Admin, resort_id: int) -> Resort:
    """
    Returns the resort only if the manager is allowed to manage it:
    - a master manages every resort of their organization
    - an admin manages the one resort they are assigned to

    A resort that does not exist, was removed, or belongs to someone else all get the same 404, so a manager
    cannot find out which resort ids exist.
    """

    ownership = (
        (Resort.id == user.resort_id) if isinstance(user, Admin) else (Resort.organization_id == user.organization_id)
    )

    resort = session.scalars(
        select(Resort).where(
            and_(
                Resort.id == resort_id,
                ownership,
                Resort.deleted_at.is_(None),
            )
        )
    ).one_or_none()

    if not resort:

        raise HTTPException(status_code=404, detail=ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name)

    return resort
