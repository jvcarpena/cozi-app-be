from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import Body, HTTPException, Path
from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, StringConstraints, field_validator
from sqlalchemy.exc import IntegrityError

from core.models.admin import Admin
from core.models.manager_verification import ManagerVerification
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from core.services.user_id_generator import generate_user_id
from domains.guest.dtos.sign_up_login_dto import validate_name_characters
from domains.manager.auth.get_manager_by_email import get_manager_by_email
from domains.manager.enums import ManagerErrorMessage
from domains.manager.resort.admin.services.admin_invite import add_invite_request, send_admin_invite_email
from domains.manager.resort.admin.services.get_resort_admin import get_resort_admin
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.get_managed_resort import get_managed_resort

Name = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50), AfterValidator(validate_name_characters)
]


class InviteAdminRequestDTO(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    first_name: Name
    last_name: Name
    phone: Optional[Annotated[str, StringConstraints(strip_whitespace=True, max_length=50)]] = None

    @field_validator("phone")
    @classmethod
    def empty_phone_is_no_phone(cls, phone: Optional[str]) -> Optional[str]:

        return phone or None


@dataclass
class InviteAdminContext:
    user: AutoMasterUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]
    request_dto: Annotated[InviteAdminRequestDTO, Body()]


def invite_admin(context: InviteAdminContext) -> GetResortDetailResponseDTO:
    """
    A master invites someone to manage one of their resorts. The admin is created without a password, and gets
    a link to set one. Setting it also proves the email, so the admin is verified at the same moment.
    """

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    # A RESORT HAS AT MOST ONE ADMIN

    if get_resort_admin(context.session, resort.id):

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.RESORT_ALREADY_HAS_ADMIN.name)

    # AN EMAIL BELONGS TO ONE MASTER OR ADMIN. THE EMAIL OF A REMOVED ADMIN IS FREE AGAIN.

    if get_manager_by_email(context.session, context.request_dto.email):

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.EMAIL_REGISTERED.name)

    # SAVE THE ADMIN WITH NO PASSWORD, NOT VERIFIED YET, AND THEIR INVITE LINK IN ONE TRANSACTION

    admin = Admin(
        id=generate_user_id(),
        email_address=context.request_dto.email,
        first_name=context.request_dto.first_name,
        last_name=context.request_dto.last_name,
        phone_number=context.request_dto.phone,
        resort_id=resort.id,
    )

    admin.verification = ManagerVerification(manager_id=admin.id, latest_email_sent_at=datetime.now(tz=timezone.utc))

    context.session.add(admin)

    try:

        context.session.flush()

        invite_request = add_invite_request(context.session, admin)

        context.session.commit()

    except IntegrityError:

        context.session.rollback()

        # TWO INVITES FOR THE SAME RESORT CAN PASS THE CHECK ABOVE TOGETHER, THE UNIQUE resort_id STOPS THE SECOND ONE.

        if get_resort_admin(context.session, resort.id):

            raise HTTPException(status_code=400, detail=ManagerErrorMessage.RESORT_ALREADY_HAS_ADMIN.name)

        raise

    # THE EMAIL IS QUEUED ONLY AFTER THE COMMIT, SO A LINK NEVER POINTS TO A REQUEST THAT WAS NOT SAVED

    send_admin_invite_email(context.user, resort, admin, invite_request)

    return build_resort_detail(context.session, context.user, resort)
