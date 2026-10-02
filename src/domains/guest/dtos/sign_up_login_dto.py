import re
from typing import Annotated

from fastapi import HTTPException
from pydantic import BaseModel, EmailStr, AfterValidator

from domains.guest.enums import GuestErrorMessage


def validate_name_characters(name: str) -> str:

    pattern = re.compile(r"[^a-zA-z\s-]")

    invalid_name_character = pattern.search(name)

    if invalid_name_character:

        raise HTTPException(status_code=400, detail=GuestErrorMessage.INVALID_NAME.name)

    return name


def check_if_empty_str(value: str):

    if value == "":

        return None

    return value


class EncryptedDataDTO(BaseModel):

    data: str


class DecryptedSignUpDataDTO(BaseModel):

    email: EmailStr

    first_name: Annotated[str, AfterValidator(validate_name_characters)]

    last_name: Annotated[str, AfterValidator(validate_name_characters)]

    phone: Annotated[str, AfterValidator(check_if_empty_str)]

    password: str


class DecryptedLoginDataDTO(BaseModel):

    email: EmailStr

    password: str


class DecryptedPasswordResetDTO(BaseModel):

    email: EmailStr
