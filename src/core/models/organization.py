from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from core.models.base import AuditMixin, Base


class Organization(Base, AuditMixin):

    __tablename__ = "organizations"

    id: Mapped[int] = mapped_column(autoincrement=True, primary_key=True)

    name: Mapped[str] = mapped_column(String(256))
