from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Numeric, func, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class CampusEnum(str, Enum):
    PALMARES = "PALMARES"
    AURORAS = "AURORAS"
    LIBERDADE = "LIBERDADE"


class Restaurant(Base):
    __tablename__ = "restaurants"

    # todos os campos não not null, nullable=False é o default do SQLAlchemy, então não precisa ser declarado explicitamente
    # default: valor gerado pelo SQLAlchemy/Python antes do INSERT
    # server_default: valor gerado pelo banco de dados durante o INSERT, ex: is_active BOOLEAN DEFAULT true
    # text() transforma o valor em SQL literal para o banco usar como DEFAULT

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    public_id: Mapped[UUID] = mapped_column(
        default=uuid4,
        unique=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(unique=True)

    campus: Mapped[CampusEnum] = mapped_column(
        SQLEnum(CampusEnum, name="campus_enum"), unique=True
    )

    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6))

    geofence_radius_m: Mapped[int] = mapped_column(
        server_default=text("80"), default=80
    )

    is_active: Mapped[bool] = mapped_column(server_default=text("true"), default=True)

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
    )
