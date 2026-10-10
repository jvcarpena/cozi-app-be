from datetime import datetime, timezone

import bcrypt
from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models.manager_password_reset_request import ManagerLinkPurpose
from core.models.user import User
from core.services.password_reset_token_handler import PasswordResetTokenError
from domains.guest.dtos.sign_up_login_dto import validate_password_length
from domains.manager.auth.get_active_password_reset_request import get_active_password_reset_request
from domains.manager.enums import ManagerErrorMessage


def reset_password(token: str, new_password: str, confirm_password: str, session: Session) -> bool:
    """
    :return: True if the link was an invite (the admin just set their first password), False for a password reset.
    """

    # CHECK IF THE NEW PASSWORD AND THE CONFIRMATION MATCH

    if new_password != confirm_password:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.PASSWORD_MISMATCH.name)

    # CHECK THE PASSWORD LENGTH

    validate_password_length(new_password)

    # GET THE REQUEST THE TOKEN WAS ISSUED FOR, IT MUST NOT BE EXPIRED OR CONSUMED.
    # THE ROW IS LOCKED SO TWO SIMULTANEOUS SUBMISSIONS CANNOT BOTH USE THE SAME LINK.

    reset_request = get_active_password_reset_request(token, session, for_update=True)

    manager = session.get(User, reset_request.manager_id)

    # A MANAGER THAT WAS REMOVED AFTER THE LINK WAS SENT CANNOT USE IT.

    if manager.deleted_at is not None:

        raise HTTPException(status_code=400, detail=PasswordResetTokenError.INVALID_OR_EXPIRED_TOKEN.name)

    # UPDATE THE MANAGER'S PASSWORD AND CONSUME THE REQUEST

    manager.hashed_password = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt())

    reset_request.request_consumed_at = datetime.now(tz=timezone.utc)

    # THE LINK WAS EMAILED TO THEM, SO USING IT ALSO PROVES THE EMAIL IS THEIRS.
    # THIS IS HOW AN ADMIN INVITED BY A MASTER BECOMES VERIFIED.

    if manager.verification is not None and manager.verification.verified_at is None:

        manager.verification.verified_at = datetime.now(tz=timezone.utc)

    was_invite = reset_request.purpose == ManagerLinkPurpose.INVITE

    session.commit()

    return was_invite
