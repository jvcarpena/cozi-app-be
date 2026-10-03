from typing import Annotated

from fastapi import Depends, HTTPException
from fastapi.security import APIKeyHeader
from sqlalchemy import select

from core.models.admin import Admin
from core.models.guest import Guest
from core.models.master import Master
from core.models.user import User
from core.services.auth_token_handler import AuthTokenHandler, TokenError
from core.services.auto_session import AutoSession


def get_auto_user(
    session: AutoSession,
    authorization_token: Annotated[str, Depends(APIKeyHeader(name="Authorization"))],
) -> User:

    decoded_token = AuthTokenHandler(token=authorization_token).decode_auth_token()

    user = session.scalars(select(User).where(User.id == decoded_token.user_id)).one()

    # A REMOVED USER KEEPS A TOKEN THAT IS STILL VALID FOR DAYS, SO THE TOKEN ALONE CANNOT BE TRUSTED.

    if user.deleted_at is not None:

        raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

    return user


AutoUser = Annotated[User, Depends(get_auto_user)]


def get_auto_guest(user: AutoUser):

    # A TOKEN ISSUED TO ANY OTHER USER TYPE (E.G. A MANAGER) MUST NOT WORK ON GUEST ENDPOINTS.

    if not isinstance(user, Guest):

        raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

    return user


AutoGuestUser = Annotated[Guest, Depends(get_auto_guest)]


def get_auto_master(user: AutoUser):

    # ONLY A MASTER CAN USE A MASTER ENDPOINT, EVEN IF THE TOKEN BELONGS TO A VALID ADMIN OR GUEST.

    if isinstance(user, Admin):

        raise HTTPException(status_code=403, detail=TokenError.MASTER_ONLY.name)

    if isinstance(user, Guest):

        raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

    return user


AutoMasterUser = Annotated[Master, Depends(get_auto_master)]


def get_auto_admin(user: AutoUser):

    if not isinstance(user, Admin):

        raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

    return user


AutoAdminUser = Annotated[Admin, Depends(get_auto_admin)]


def get_auto_manager(user: AutoUser):

    # A MANAGER IS EITHER A MASTER OR AN ADMIN. A TOKEN ISSUED TO A GUEST MUST NOT WORK ON MANAGER ENDPOINTS.

    if not isinstance(user, (Master, Admin)):

        raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

    return user


AutoManagerUser = Annotated[Master | Admin, Depends(get_auto_manager)]
