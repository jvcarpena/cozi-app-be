from typing import Annotated

from fastapi import APIRouter, Path

from core.services.auto_session import AutoSession
from domains.guest.resort.get_resort_details_service import get_resort_details
from domains.guest.resort.get_resorts_service import get_resorts, GetResortsResponseDTO

resort_router = APIRouter(prefix="/resorts")


@resort_router.get("")
def do_get_resorts(session: AutoSession) -> GetResortsResponseDTO:

    return get_resorts(session)


@resort_router.get("/{resort_id}")
def do_get_resort_details(resort_id: Annotated[int, Path(...)], session: AutoSession):

    return get_resort_details(resort_id, session)
