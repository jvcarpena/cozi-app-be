from dataclasses import dataclass
from typing import Annotated

from fastapi import Path

from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.manager.resort.services.build_resort_detail import GetResortDetailResponseDTO, build_resort_detail
from domains.manager.resort.services.get_managed_resort import get_managed_resort


@dataclass
class GetResortDetailContext:
    user: AutoManagerUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]


def get_resort_detail(context: GetResortDetailContext) -> GetResortDetailResponseDTO:

    resort = get_managed_resort(context.session, context.user, context.resort_id)

    return build_resort_detail(context.session, context.user, resort)
