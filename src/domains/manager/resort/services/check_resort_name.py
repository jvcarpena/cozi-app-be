from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select, exists, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core.models.resort import Resort
from domains.manager.enums import ManagerErrorMessage

UNIQUE_RESORT_NAME_CONSTRAINT = "uq_resorts_organization_id_name"


def check_resort_name_is_free(
    session: Session, organization_id: int, name: str, exclude_resort_id: Optional[int] = None
):
    """
    A resort name must be unique inside its organization. Two different organizations can use the same name.
    Pass the id of the resort that is being renamed so it does not clash with itself.
    """

    conditions = [
        Resort.organization_id == organization_id,
        Resort.name == name,
        Resort.deleted_at.is_(None),
    ]

    if exclude_resort_id is not None:

        conditions.append(Resort.id != exclude_resort_id)

    if session.scalars(select(exists().where(and_(*conditions)))).one():

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name)


def commit_resort(session: Session):
    """
    Commits, and turns the database's unique name constraint into the same error as check_resort_name_is_free.
    The check above can pass for two requests at the same moment, the constraint is what really guarantees it.
    """

    try:

        session.commit()

    except IntegrityError as error:

        session.rollback()

        if UNIQUE_RESORT_NAME_CONSTRAINT not in str(error.orig):

            raise

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.RESORT_NAME_ALREADY_EXISTS.name)
