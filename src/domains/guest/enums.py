from enum import StrEnum


class GuestErrorMessage(StrEnum):
    INVALID_NAME = "Guest name is invalid."
    EMAIL_REGISTERED = "Email is already registered."
