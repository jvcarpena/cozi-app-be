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


class EncryptedDataDTO(BaseModel):

    ciphertext: str

    nonce: str

    tag: str


class DecryptedSignUpDataDTO(BaseModel):

    email: EmailStr

    first_name: Annotated[str, AfterValidator(validate_name_characters)]

    last_name: Annotated[str, AfterValidator(validate_name_characters)]

    password: str


class DecryptedLoginDataDTO(BaseModel):

    email: EmailStr

    password: str
