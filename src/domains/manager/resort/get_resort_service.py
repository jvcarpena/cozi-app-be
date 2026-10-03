from dataclasses import dataclass
from decimal import Decimal
from typing import List, Sequence

from pydantic import BaseModel
from select import select
from sqlalchemy import and_

from core.models.admin import Admin
from core.models.resort import ResortStatusEnum, Resort
from core.services.auto_session import AutoSession
from core.services.auto_user import AutoManagerUser


@dataclass
class GetResortContext:
    user: AutoManagerUser
    session: AutoSession


class ResortDTO(BaseModel):
    id: int
    name: str
    status: ResortStatusEnum
    address: str
    base_price_per_day_use: Decimal
    base_price_per_night: Decimal


class GetResortResponseDTO(BaseModel):

    resorts: List[ResortDTO]


def get_resort(context: GetResortContext):

    expression_based_on_user = (
        (Resort.id == context.user.resort_id)
        if isinstance(context.user, Admin)
        else (Resort.organization_id == context.user.organization_id)
    )

    resorts: Sequence[Resort] = context.session.scalars(
        select(Resort).where(
            and_(
                expression_based_on_user,
                Resort.deleted_at.isnot(None),
            )
        )
    ).all()

    resorts_dto: List[ResortDTO] = [
        ResortDTO(
            id=resort.id,
            name=resort.name,
            status=resort.status,
            address=resort.address,
            base_price_per_day_use=resort.base_price_per_day_use,
            base_price_per_night=resort.base_price_per_night,
        )
        for resort in resorts
    ]

    return GetResortResponseDTO(resorts=resorts_dto)
