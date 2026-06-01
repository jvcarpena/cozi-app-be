from typing import Annotated

from fastapi import Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import select

from core.models.guest import Guest
from core.models.user import User
from core.services.auth_token_handler import AuthTokenHandler
from core.services.auto_session import AutoSession


def get_auto_user(
    session: AutoSession,
    authorization_token: Annotated[str, Depends(APIKeyHeader(name="Authorization"))],
) -> User:

    decoded_token = AuthTokenHandler(token=authorization_token).decode_auth_token()

    user = session.scalars(select(User).where(User.id == decoded_token.user_id)).one()

    return user


AutoUser = Annotated[User, Depends(get_auto_user)]


def get_auto_guest(user: AutoUser):

    assert isinstance(user, Guest)

    return user


AutoGuestUser = Annotated[Guest, Depends(get_auto_guest)]
