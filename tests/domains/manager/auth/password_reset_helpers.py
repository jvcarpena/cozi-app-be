from core.models.manager_password_reset_request import ManagerPasswordResetRequest
from core.services.password_reset_token_handler import MANAGER_PURPOSE, PasswordResetTokenHandler


def build_reset_token(reset_request: ManagerPasswordResetRequest) -> str:
    """
    Builds the same token the forgot password endpoint emails to the manager.
    """

    return PasswordResetTokenHandler(
        request_id=reset_request.id, expiry_date=reset_request.expires_at, purpose=MANAGER_PURPOSE
    ).generate_reset_token()


def build_guest_reset_token(reset_request: ManagerPasswordResetRequest) -> str:
    """
    Builds a password reset token in the guest format, pointing at the same request id.
    """

    return PasswordResetTokenHandler(
        request_id=reset_request.id, expiry_date=reset_request.expires_at
    ).generate_reset_token()
