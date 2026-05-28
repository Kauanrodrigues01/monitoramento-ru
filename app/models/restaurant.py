from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

if TYPE_CHECKING:  # pragma: no cover
    from app.models.queue_reports import QueueReport
    from app.models.queue_snapshot import QueueSnapshot

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class ExceptionTypeEnum(str, Enum):
    CLOSED = "CLOSED"
    CUSTOM_HOURS = "CUSTOM_HOURS"


class CampusEnum(str, Enum):
    PALMARES = "PALMARES"
    AURORAS = "AURORAS"
    LIBERDADE = "LIBERDADE"


class MealPeriodEnum(str, Enum):
    LUNCH = "LUNCH"
    DINNER = "DINNER"


meal_period_sqlenum = SQLEnum(
    MealPeriodEnum,
    name="meal_period_enum",
    create_type=False,
)


class Restaurant(Base):
    __tablename__ = "restaurants"

    # todos os campos não not null, nullable=False é o default do SQLAlchemy, então não precisa ser declarado explicitamente
    # default: valor gerado pelo SQLAlchemy/Python antes do INSERT
    # server_default: valor gerado pelo banco de dados durante o INSERT, ex: is_active BOOLEAN DEFAULT true
    # text() transforma o valor em SQL literal para o banco usar como DEFAULT

    id: Mapped[int] = mapped_column(primary_key=True)

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
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    schedules: Mapped[list["RestaurantSchedule"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )

    schedule_exceptions: Mapped[list["RestaurantScheduleException"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )

    reports: Mapped[list["QueueReport"]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
    )

    snapshots: Mapped[list["QueueSnapshot"]] = relationship(
        back_populates="restaurant", cascade="all, delete-orphan"
    )


class RestaurantSchedule(Base):
    __tablename__ = "restaurant_schedules"

    __table_args__ = (
        # Garante que weekday esteja entre 0 e 5 (dias permitidos)
        CheckConstraint(
            "weekday BETWEEN 0 AND 5",
            name="ck_weekday_between_0_and_5",
        ),
        # Impede duplicidade:
        # um RU não pode ter dois horários iguais
        # para o mesmo dia + período
        UniqueConstraint(
            "ru_id",
            "weekday",
            "meal_period",
            name="uq_restaurant_schedule",
        ),
        # Índice para acelerar consultas frequentes por:
        # RU + dia + período
        Index(
            "ix_restaurant_schedule_lookup",
            "ru_id",
            "weekday",
            "meal_period",
        ),
        CheckConstraint(
            "opens_at IS NULL OR closes_at IS NULL OR opens_at < closes_at",
            name="ck_schedule_opens_before_closes",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    public_id: Mapped[UUID] = mapped_column(
        default=uuid4,
        unique=True,
        index=True,
    )

    # ForeignKey cria o vínculo no banco:
    # muitos schedules pertencem a um restaurant
    ru_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
    )

    weekday: Mapped[int]

    meal_period: Mapped[MealPeriodEnum] = mapped_column(meal_period_sqlenum)

    # datetime.time -> SQL TIME
    # Ex: 11:00:00
    opens_at: Mapped[time]
    closes_at: Mapped[time]

    is_active: Mapped[bool] = mapped_column(
        server_default=text("true"),
        default=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # relationship é navegação ORM:
    # schedule.restaurant
    #
    # back_populates conecta os dois lados:
    # restaurant.schedules <-> schedule.restaurant
    restaurant: Mapped[Restaurant] = relationship(back_populates="schedules")


class RestaurantScheduleException(Base):
    """Representa uma exceção ao horário regular de um restaurante em uma data específica.

    Casos possíveis:

    1. RU fechado o dia todo (ambos os períodos):
       exception_type=CLOSED, meal_period=None, opens_at=None, closes_at=None
       → Garantido único por índice parcial (uq_restaurant_schedule_exception_whole_day).

    2. RU fechado em um período específico:
       exception_type=CLOSED, meal_period=LUNCH|DINNER, opens_at=None, closes_at=None
       → Ex.: apenas o jantar cancelado em um feriado com almoço normal.

    3. Horário especial em um período específico:
       exception_type=CUSTOM_HOURS, meal_period=LUNCH|DINNER, opens_at=HH:MM, closes_at=HH:MM
       → Ex.: almoço com horário reduzido numa sexta-feira de evento.

    Restrições:
    - CUSTOM_HOURS exige opens_at e closes_at; CLOSED não pode tê-los.
    - Um mesmo RU pode ter no máximo uma exceção de dia inteiro (meal_period=None)
      e uma por período (LUNCH, DINNER) por data — garantido pelos constraints únicos.
    - Não é possível ter simultaneamente uma exceção de dia inteiro e uma por período
      na mesma data (seria redundante; o dia inteiro já cobre tudo).
    """

    __tablename__ = "restaurant_schedule_exceptions"

    __table_args__ = (
        # unicidade quando meal_period está preenchido
        UniqueConstraint(
            "ru_id",
            "exception_date",
            "meal_period",
            name="uq_restaurant_schedule_exception",
        ),
        # unicidade para exceções de dia inteiro (meal_period IS NULL):
        # UniqueConstraint ignora NULLs no PostgreSQL, então é necessário um índice parcial
        Index(
            "uq_restaurant_schedule_exception_whole_day",
            "ru_id",
            "exception_date",
            unique=True,
            postgresql_where=text("meal_period IS NULL"),
        ),
        Index(
            "ix_schedule_exception_lookup",
            "ru_id",
            "exception_date",
        ),
        CheckConstraint(
            "opens_at IS NULL OR closes_at IS NULL OR opens_at < closes_at",
            name="ck_exception_opens_before_closes",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    public_id: Mapped[UUID] = mapped_column(
        default=uuid4,
        unique=True,
        index=True,
    )

    ru_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
    )

    exception_date: Mapped[date] = mapped_column(Date)

    exception_type: Mapped[ExceptionTypeEnum] = mapped_column(
        SQLEnum(
            ExceptionTypeEnum,
            name="exception_type_enum",
        )
    )

    # null = exceção se aplica ao dia inteiro (ambos os períodos)
    meal_period: Mapped[MealPeriodEnum | None] = mapped_column(
        meal_period_sqlenum,
        nullable=True,
    )

    # preenchidos apenas quando exception_type = CUSTOM_HOURS
    opens_at: Mapped[time | None]
    closes_at: Mapped[time | None]

    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="schedule_exceptions")
