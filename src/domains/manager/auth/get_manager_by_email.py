from sqlalchemy import select
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.master import Master
from core.models.user import User

MANAGER_USER_TYPES = ["master", "admin"]


def get_manager_by_email(session: Session, email: str) -> Master | Admin | None:
    """
    Finds the master or the admin that uses the email. A removed manager is never returned, so their email is free again.
    """

    return session.scalars(
        select(User).where(
            User.email_address == email,
            User.user_type.in_(MANAGER_USER_TYPES),
            User.deleted_at.is_(None),
        )
    ).one_or_none()
