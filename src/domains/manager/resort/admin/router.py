from typing import Annotated

from fastapi import APIRouter, Depends

from domains.manager.resort.admin.invite_admin_service import InviteAdminContext, invite_admin
from domains.manager.resort.admin.remove_admin_service import RemoveAdminContext, remove_admin
from domains.manager.resort.admin.resend_admin_invite_service import ResendAdminInviteContext, resend_admin_invite
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO

admin_router = APIRouter(prefix="/{resort_id}/admin")


@admin_router.post("")
def do_invite_admin(context: Annotated[InviteAdminContext, Depends()]) -> GetResortDetailResponseDTO:

    return invite_admin(context)


@admin_router.post("/resend")
def do_resend_admin_invite(context: Annotated[ResendAdminInviteContext, Depends()]) -> GetResortDetailResponseDTO:

    return resend_admin_invite(context)


@admin_router.delete("")
def do_remove_admin(context: Annotated[RemoveAdminContext, Depends()]) -> GetResortDetailResponseDTO:

    return remove_admin(context)
