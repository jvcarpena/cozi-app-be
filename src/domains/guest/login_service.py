from pydantic import BaseModel


class InitialResponseDTO(BaseModel):

    message: str


def login():
    return InitialResponseDTO(message="HELLO GUEST!")
