from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models.guest import Guest
from domains.guest.auth.get_active_password_reset_request import get_active_password_reset_request
from domains.guest.enums import GuestErrorMessage

# BCRYPT ONLY USES THE FIRST 72 BYTES OF A PASSWORD, THE NEWER VERSIONS REJECT ANYTHING LONGER.
MAX_PASSWORD_BYTES = 72


def reset_password(token: str, new_password: str, confirm_password: str, session: Session):

    # CHECK IF THE NEW PASSWORD AND THE CONFIRMATION MATCH

    if new_password != confirm_password:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.PASSWORD_MISMATCH.name)

    # CHECK THE PASSWORD IS NOT TOO LONG

    if len(new_password.encode("utf-8")) > MAX_PASSWORD_BYTES:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.INVALID_PASSWORD_LENGTH.name)

    # GET THE REQUEST THE TOKEN WAS ISSUED FOR, IT MUST NOT BE EXPIRED OR CONSUMED.
    # THE ROW IS LOCKED SO TWO SIMULTANEOUS SUBMISSIONS CANNOT BOTH USE THE SAME LINK.

    reset_request = get_active_password_reset_request(token, session, for_update=True)

    guest = session.get(Guest, reset_request.guest_id)

    # UPDATE THE GUEST'S PASSWORD AND CONSUME THE REQUEST

    guest.hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

    reset_request.request_consumed_at = datetime.now(tz=timezone.utc)

    session.commit()

    return
