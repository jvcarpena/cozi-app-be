from enum import StrEnum


class GuestErrorMessage(StrEnum):
    INVALID_NAME = "Guest name is invalid."
    EMAIL_REGISTERED = "Email is already registered."
    ACCOUNT_DOES_NOT_EXISTS = "Account does not exists."
    LINK_EXPIRED = "Verification link expired."
    CHECK_YOUR_EMAIL = "Check your email for verification."
    EMAIL_NOT_EXISTS = "Email does not exists."
    EMAIL_NOT_VERIFIED = "Email does not verified."
    INVALID_CREDENTIALS = "Invalid credentials."
