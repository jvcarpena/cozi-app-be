from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import HTTPException, Path

from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from domains.manager.enums import ManagerErrorMessage
from domains.manager.resort.admin.services.admin_invite import close_open_invites
from domains.manager.resort.admin.services.get_resort_admin import get_resort_admin
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.get_managed_resort import get_managed_resort

# WHAT IS LEFT OF A REMOVED ADMIN. THE ROW STAYS AS A RECORD, BUT NOTHING ABOUT THE PERSON.
REMOVED_ADMIN_FIRST_NAME = "DELETED"
REMOVED_ADMIN_LAST_NAME = "ADMIN"


@dataclass
class RemoveAdminContext:
    user: AutoMasterUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]


def remove_admin(context: RemoveAdminContext) -> GetResortDetailResponseDTO:
    """
    Removes the admin of a resort. The admin can no longer log in, and the email and the resort are free again:
    inviting the same person (or someone else) later creates a new admin.
    """

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    admin = get_resort_admin(context.session, resort.id, for_update=True)

    if not admin:

        raise HTTPException(status_code=404, detail=ManagerErrorMessage.ADMIN_DOES_NOT_EXIST.name)

    # NO LINK THAT WAS ALREADY SENT (INVITE OR PASSWORD RESET) CAN BRING THE ACCOUNT BACK

    close_open_invites(context.session, admin.id)

    # THE REMOVAL: THE TOKEN OF THE ADMIN IS REFUSED BECAUSE deleted_at IS SET, THE REST OF THE PERSONAL DATA IS CLEARED,
    # AND THE EMAIL AND THE RESORT ARE RELEASED.

    admin.deleted_at = datetime.now(tz=timezone.utc)

    admin.first_name = REMOVED_ADMIN_FIRST_NAME

    admin.last_name = REMOVED_ADMIN_LAST_NAME

    admin.email_address = None

    admin.phone_number = None

    admin.hashed_password = None

    admin.profile_picture = None

    admin.active_token = None

    admin.resort_id = None

    context.session.commit()

    return build_resort_detail(context.session, context.user, resort)
