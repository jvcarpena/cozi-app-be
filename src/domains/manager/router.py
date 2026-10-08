from fastapi import APIRouter

from domains.manager.auth.router import auth_router
from domains.manager.resort.router import resort_router

manager_router = APIRouter(prefix="/manager")

manager_router.include_router(auth_router)
manager_router.include_router(resort_router)
