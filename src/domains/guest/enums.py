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
    RESORT_DOES_NOT_EXIST = "Resort does not exist."
    RESORT_IS_NOT_AVAILABLE = "Resort is not available on selected date."
    NUMBER_OF_GUESTS_EXCEEDS_RESORT_CAPACITY = "Number of guests exceeds resort capacity."
    BOOKING_DOES_NOT_EXIST = "Booing does not exist."
    CHECKOUT_MUST_BE_AFTER_CHECK_IN = "Check out must be after check in"
    NUM_GUEST_MUST_BE_AT_LEAST_1 = "Num guest must be at least 1"
    PASSWORD_MISMATCH = "New password and confirm password do not match."
    INVALID_PASSWORD_LENGTH = "Password must be 6 to 72 characters long."
