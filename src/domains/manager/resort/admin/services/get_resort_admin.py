from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from core.models.admin import Admin


def get_resort_admin(session: Session, resort_id: int, for_update: bool = False) -> Optional[Admin]:
    """
    The admin who currently manages the resort, or None. A removed admin has no resort, so only the current one
    can match. Pass for_update to lock the row, so two requests cannot change the same admin at the same time.
    """

    query = select(Admin).where(
        and_(
            Admin.resort_id == resort_id,
            Admin.deleted_at.is_(None),
        )
    )

    if for_update:

        query = query.with_for_update()

    return session.scalars(query).one_or_none()
