from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import Path, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from core.models.admin import Admin
from core.models.master import Master
from core.models.resort import ResortStatusEnum, Resort
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser
from domains.manager.enums import ManagerErrorMessage


@dataclass
class GetResortDetailContext:
    user: AutoManagerUser
    session: AutoSession
    resort_id: Annotated[int, Path(...)]


class AdminDTO(BaseModel):
    id: str
    email: EmailStr
    first_name: str
    last_name: str


class ResortDetailDTO(BaseModel):
    id: int
    admin: Optional[AdminDTO] = None
    organization_id: int
    name: str
    status: ResortStatusEnum
    description: str
    base_price_per_night: Decimal
    base_price_per_day_use: Decimal
    currency: str
    max_guests: int
    num_bedrooms: int
    num_bathrooms: int
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    address: str


class GetResortDetailResponseDTO(BaseModel):
    resort: ResortDetailDTO


def get_resort_detail(context: GetResortDetailContext):

    resort: Resort = context.session.scalars(select(Resort).where(Resort.id == context.resort_id)).one_or_none()

    if not resort:
        raise HTTPException(status_code=404, detail=ManagerErrorMessage.RESORT_DOES_NOT_EXIST.name)

    admin_dto = None
    if isinstance(context.user, Master):
        admin = context.session.scalars(select(Admin).where(Admin.resort_id == context.resort_id)).one_or_none()

        if admin:
            admin_dto = AdminDTO(
                id=admin.id,
                email=admin.email_address,
                first_name=admin.first_name,
                last_name=admin.last_name,
            )

    resort_dto = ResortDetailDTO(
        id=resort.id,
        admin=admin_dto,
        organization_id=resort.organization_id,
        name=resort.name,
        status=resort.status,
        description=resort.description,
        base_price_per_night=resort.base_price_per_night,
        base_price_per_day_use=resort.base_price_per_day_use,
        currency=resort.currency,
        max_guests=resort.max_guests,
        num_bedrooms=resort.num_bedrooms,
        num_bathrooms=resort.num_bathrooms,
        latitude=resort.latitude,
        longitude=resort.longitude,
        address=resort.address,
    )

    return GetResortDetailResponseDTO(resort=resort_dto)
