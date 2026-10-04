from typing import Annotated

from fastapi import APIRouter, Depends

from domains.manager.resort.create_resort_service import CreateResortContext, create_resort
from domains.manager.resort.get_resort_detail_service import GetResortDetailContext, get_resort_detail
from domains.manager.resort.get_resort_service import GetResortContext, get_resort
from domains.manager.resort.update_resort_pricing_service import UpdateResortPricingContext, update_resort_pricing
from domains.manager.resort.update_resort_status_service import update_resort_status, UpdateResortStatusContext

resort_router = APIRouter(prefix="/resorts")


@resort_router.post("")
def do_create_resort(context: Annotated[CreateResortContext, Depends()]):

    return create_resort(context)


@resort_router.get("")
def do_get_resort(context: Annotated[GetResortContext, Depends()]):

    return get_resort(context)


@resort_router.get("/{id}")
def do_get_resort_detail(context: Annotated[GetResortDetailContext, Depends()]):

    return get_resort_detail(context)


@resort_router.put("/{id}/pricing")
def do_update_resort_pricing(context: Annotated[UpdateResortPricingContext, Depends()]):

    return update_resort_pricing(context)


@resort_router.put("/{id}/status")
def do_update_resort_status(context: Annotated[UpdateResortStatusContext, Depends()]):

    return update_resort_status(context)
