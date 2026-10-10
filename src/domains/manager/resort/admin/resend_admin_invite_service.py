from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Annotated

from fastapi import HTTPException, Path

from core.services.auto_session import AutoSession
from core.services.auto_user import AutoMasterUser
from domains.manager.enums import ManagerErrorMessage
from domains.manager.resort.admin.services.admin_invite import (
    ADMIN_INVITE_RESEND_COOLDOWN,
    add_invite_request,
    close_open_invites,
    send_admin_invite_email,
)
from domains.manager.resort.admin.services.get_resort_admin import get_resort_admin
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.get_managed_resort import get_managed_resort


@dataclass
class ResendAdminInviteContext:
    user: AutoMasterUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]


def resend_admin_invite(context: ResendAdminInviteContext) -> GetResortDetailResponseDTO:
    """
    Sends a new invite link to an admin who has not set a password yet. The older link stops working.
    """

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    # THE ADMIN ROW IS LOCKED, SO TWO RESENDS AT THE SAME MOMENT CANNOT BOTH PASS THE COOLDOWN

    admin = get_resort_admin(context.session, resort.id, for_update=True)

    if not admin:

        raise HTTPException(status_code=404, detail=ManagerErrorMessage.ADMIN_DOES_NOT_EXIST.name)

    # AN ADMIN WHO ALREADY SET A PASSWORD DOES NOT NEED AN INVITE

    if admin.verification.verified_at is not None:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.ADMIN_ALREADY_ACTIVE.name)

    current_datetime_utc = datetime.now(tz=timezone.utc)

    if admin.verification.latest_email_sent_at > current_datetime_utc - ADMIN_INVITE_RESEND_COOLDOWN:

        raise HTTPException(status_code=400, detail=ManagerErrorMessage.INVITE_RECENTLY_SENT.name)

    close_open_invites(context.session, admin.id)

    invite_request = add_invite_request(context.session, admin)

    admin.verification.latest_email_sent_at = current_datetime_utc

    context.session.commit()

    send_admin_invite_email(context.user, resort, admin, invite_request)

    return build_resort_detail(context.session, context.user, resort)
