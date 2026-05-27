from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    PrimaryKeyConstraint,
    func,
    text,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.queue_reports import confidence_score_constraint
from app.models.restaurant import MealPeriodEnum, Restaurant, meal_period_sqlenum


class SnapshotStatusEnum(str, Enum):
    NO_QUEUE = "NO_QUEUE"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    FOOD_ENDED = "FOOD_ENDED"
    NO_DATA = "NO_DATA"


class QueueSnapshot(Base):
    __tablename__ = "queue_snapshots"

    __table_args__ = (
        PrimaryKeyConstraint(  # Já cria indice para ru_id e meal_period
            "ru_id",
            "meal_period",
            name="pk_ru_id_meal_period",
        ),
        CheckConstraint(
            "reports_last_15m >= 0",
            name="ck_reports_last_15m_positive",
        ),
        confidence_score_constraint,
    )

    # Primary key composto por ru_id e meal_period, com isso:
    # sempre existem exatamente 2 linhas por restaurante:
    # (ru_id, LUNCH) e (ru_id, DINNER)

    ru_id: Mapped[int] = mapped_column(
        ForeignKey(
            "restaurants.id",
            ondelete="CASCADE",
        ),
    )

    meal_period: Mapped[MealPeriodEnum] = mapped_column(meal_period_sqlenum)

    current_status: Mapped[SnapshotStatusEnum] = mapped_column(
        SQLEnum(
            SnapshotStatusEnum,
            name="queue_snapshot_status_enum",
        ),
        default=SnapshotStatusEnum.NO_DATA,
        server_default=text(f"'{SnapshotStatusEnum.NO_DATA.value}'"),
    )

    reports_last_15m: Mapped[int] = mapped_column(default=0, server_default=text("0"))

    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("1.00"),
        server_default=text("1.00"),
    )

    override_active: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )

    last_report_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="snapshots")

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
