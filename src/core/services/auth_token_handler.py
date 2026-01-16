import os
from datetime import datetime, timezone, timedelta
from enum import StrEnum
from typing import Optional

import jwt
from fastapi import HTTPException
from pydantic import BaseModel


class TokenError(StrEnum):

    INVALID_SESSION = "Expired token or invalid token"


class TokenDTO(BaseModel):

    user_id: str

    exp: datetime

    is_admin: Optional[bool] = False


class AuthTokenHandler:

    def __init__(self, user_id=None, expiry_date=None, is_admin=False, token=None):
        self.user_id = user_id
        self.expiry_date = expiry_date
        self.is_admin = is_admin
        self.token = token
        self.secret_key = os.environ.get("TOKEN_SECRET_KEY")

    def generate_auth_token(self):

        if not self.expiry_date:
            self.expiry_date = self._get_utc_datetime() + timedelta(days=7)

        token = TokenDTO(user_id=self.user_id, exp=self.expiry_date, is_admin=self.is_admin)

        token = jwt.encode(token.model_dump(), self.secret_key, algorithm="HS256")

        return token

    def decode_auth_token(self, verify_exp: bool = True) -> TokenDTO:

        try:

            decoded_token = jwt.decode(
                self.token,
                self.secret_key,
                algorithms=["HS256"],
                options={"verify_exp": verify_exp},
            )

        except jwt.ExpiredSignatureError:

            raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

        except jwt.InvalidTokenError:

            raise HTTPException(status_code=401, detail=TokenError.INVALID_SESSION.name)

        return TokenDTO(**decoded_token)

    def _get_utc_datetime(self):

        return datetime.now(timezone.utc).replace(tzinfo=None)


if __name__ == "__main__":

    token = AuthTokenHandler(user_id="jv1234").generate_auth_token()
    print(token)

    decoded_token = AuthTokenHandler(token=token).decode_auth_token()
    print(decoded_token)
