from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models.admin import Admin
from domains.guest.dtos.sign_up_login_dto import validate_password_length
from domains.manager.auth.get_active_password_reset_request import get_active_password_reset_request
from domains.manager.enums import ManagerErrorMessage


def reset_password(token: str, new_password: str, confirm_password: str, session: Session):

    # CHECK IF THE NEW PASSWORD AND THE CONFIRMATION MATCH

    if new_password != confirm_password:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.PASSWORD_MISMATCH.name)

    # CHECK THE PASSWORD LENGTH

    validate_password_length(new_password)

    # GET THE REQUEST THE TOKEN WAS ISSUED FOR, IT MUST NOT BE EXPIRED OR CONSUMED.
    # THE ROW IS LOCKED SO TWO SIMULTANEOUS SUBMISSIONS CANNOT BOTH USE THE SAME LINK.

    reset_request = get_active_password_reset_request(token, session, for_update=True)

    manager = session.get(Admin, reset_request.manager_id)

    # UPDATE THE MANAGER'S PASSWORD AND CONSUME THE REQUEST

    manager.hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

    reset_request.request_consumed_at = datetime.now(tz=timezone.utc)

    session.commit()

    return
