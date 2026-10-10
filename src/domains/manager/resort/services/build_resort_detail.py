from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from core.models.admin import Admin
from core.models.master import Master
from core.models.resort import Resort, ResortStatusEnum


class AdminDTO(BaseModel):
    id: str

    # PENDING: INVITED, HAS NOT SET A PASSWORD YET. ACTIVE: CAN LOG IN.
    status: Literal["PENDING", "ACTIVE"]
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None


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


def build_resort_detail(session: Session, user: Master | Admin, resort: Resort) -> GetResortDetailResponseDTO:
    """
    The response every resort endpoint returns. Only a master is shown the admin of the resort, an admin already
    knows who they are.
    """

    admin_dto = None

    if isinstance(user, Master):

        admin = session.scalars(
            select(Admin).where(
                and_(
                    Admin.resort_id == resort.id,
                    Admin.deleted_at.is_(None),
                )
            )
        ).one_or_none()

        if admin:

            is_active = admin.verification is not None and admin.verification.verified_at is not None

            admin_dto = AdminDTO(
                id=admin.id,
                status="ACTIVE" if is_active else "PENDING",
                email=admin.email_address,
                first_name=admin.first_name,
                last_name=admin.last_name,
            )

    return GetResortDetailResponseDTO(
        resort=ResortDetailDTO(
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
    )
