from typing import Annotated

from pydantic import StringConstraints

from domains.guest.dtos.sign_up_login_dto import DecryptedSignUpDataDTO


class DecryptedManagerSignUpDataDTO(DecryptedSignUpDataDTO):
    """
    Same fields as a guest sign up, plus the name of the organization the new master owns. A master with several
    resorts enters the name of the organization, a master with a single resort enters the name of the resort.
    """

    organization_name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=256)]
