from core.models.guest_password_reset_request import GuestPasswordResetRequest
from core.services.password_reset_token_handler import PasswordResetTokenHandler


def build_reset_token(reset_request: GuestPasswordResetRequest) -> str:
    """
    Builds the same token the forgot password endpoint emails to the guest.
    """

    return PasswordResetTokenHandler(
        request_id=reset_request.id, expiry_date=reset_request.expires_at
    ).generate_reset_token()
