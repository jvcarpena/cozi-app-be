import hashlib
import hmac
import os
from datetime import datetime
from enum import StrEnum

import jwt
from fastapi import HTTPException

PURPOSE = "password_reset"

MANAGER_PURPOSE = "manager_password_reset"


class PasswordResetTokenError(StrEnum):

    INVALID_OR_EXPIRED_TOKEN = "Invalid or expired password reset link"


class PasswordResetTokenHandler:
    """
    Builds and decodes the token that is emailed to a guest or a manager to reset a password.

    The token only carries the id of a row in guest_password_reset_requests (PURPOSE) or
    manager_password_reset_requests (MANAGER_PURPOSE). That row is the source of truth for expiry and single
    use. The signing key is derived from TOKEN_SECRET_KEY with the purpose label, so a reset token can never
    be accepted as a login token by AuthTokenHandler, and a guest token can never reset a manager password
    (and vice versa).
    """

    def __init__(
        self,
        request_id: int | None = None,
        expiry_date: datetime | None = None,
        token: str | None = None,
        purpose: str = PURPOSE,
    ):
        self.request_id = request_id
        self.expiry_date = expiry_date
        self.token = token
        self.purpose = purpose
        self.secret_key = hmac.new(
            os.environ.get("TOKEN_SECRET_KEY").encode("utf-8"), purpose.encode("utf-8"), hashlib.sha256
        ).digest()

    def generate_reset_token(self) -> str:

        return jwt.encode(
            {"rid": self.request_id, "purpose": self.purpose, "exp": self.expiry_date},
            self.secret_key,
            algorithm="HS256",
        )

    def decode_reset_token(self) -> int:
        """
        :return: the id of the password reset request the token was issued for.
        """

        try:

            decoded_token = jwt.decode(self.token, self.secret_key, algorithms=["HS256"])

        except jwt.InvalidTokenError:

            raise HTTPException(status_code=400, detail=PasswordResetTokenError.INVALID_OR_EXPIRED_TOKEN.name)

        if decoded_token.get("purpose") != self.purpose or not isinstance(decoded_token.get("rid"), int):

            raise HTTPException(status_code=400, detail=PasswordResetTokenError.INVALID_OR_EXPIRED_TOKEN.name)

        return decoded_token["rid"]
