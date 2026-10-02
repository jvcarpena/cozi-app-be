from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from core.services.password_reset_token_handler import (
    MANAGER_PURPOSE,
    PasswordResetTokenHandler,
    PasswordResetTokenError,
)


def get_active_password_reset_request(
    token: str, session: Session, for_update: bool = False
) -> ManagerPasswordResetRequest:
    """
    Returns the password reset request the token was issued for, only if it is not expired and not consumed yet.
    Every failure raises the same error so the response does not say why the link is not usable.
    """

    request_id = PasswordResetTokenHandler(token=token, purpose=MANAGER_PURPOSE).decode_reset_token()

    reset_request = session.get(ManagerPasswordResetRequest, request_id, with_for_update=for_update)

    if (
        not reset_request
        or reset_request.request_consumed_at
        or reset_request.expires_at <= datetime.now(tz=timezone.utc)
    ):

        raise HTTPException(status_code=400, detail=PasswordResetTokenError.INVALID_OR_EXPIRED_TOKEN.name)

    return reset_request
