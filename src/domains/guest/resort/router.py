from fastapi import APIRouter

from core.services.auto_session import AutoSession
from domains.guest.resort.get_resorts_service import get_resorts, GetResortsResponseDTO

resort_router = APIRouter(prefix="/resorts")


@resort_router.get("")
def do_get_resorts(session: AutoSession) -> GetResortsResponseDTO:

    return get_resorts(session)
