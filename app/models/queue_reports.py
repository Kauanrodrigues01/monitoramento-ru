from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.restaurant import MealPeriodEnum, Restaurant, meal_period_sqlenum


class ReportStatusEnum(str, Enum):
    NO_QUEUE = "NO_QUEUE"
    SMALL = "SMALL"
    MEDIUM = "MEDIUM"
    LARGE = "LARGE"
    FOOD_ENDED = "FOOD_ENDED"


confidence_score_constraint = CheckConstraint(
    "confidence_score >= 0.05 AND confidence_score <= 1.00",
    name="ck_confidence_score_between_0_05_and_1",
)


class QueueReport(Base):
    __tablename__ = "queue_reports"

    __table_args__ = (
        Index(
            "ix_queue_reports_lookup",
            "ru_id",
            "meal_period",
            "created_at",
        ),
        confidence_score_constraint,
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    public_id: Mapped[UUID] = mapped_column(
        default=uuid4,
        unique=True,
        index=True,
    )

    ru_id: Mapped[int] = mapped_column(ForeignKey("restaurants.id", ondelete="CASCADE"))

    status: Mapped[ReportStatusEnum] = mapped_column(
        SQLEnum(ReportStatusEnum, name="queue_report_status_enum")
    )

    meal_period: Mapped[MealPeriodEnum] = mapped_column(meal_period_sqlenum)

    lat: Mapped[Decimal] = mapped_column(Numeric(9, 6))
    lng: Mapped[Decimal] = mapped_column(Numeric(9, 6))

    # SHA-256 do IP; nunca armazenamos IP real (LGPD)
    ip_hash: Mapped[str] = mapped_column(String(64))

    accuracy_m: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 2),
        nullable=True,
    )

    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("1.00"),
        server_default=text("1.00"),
    )

    is_mock_location: Mapped[bool] = mapped_column(
        default=False, server_default=text("false")
    )

    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    restaurant: Mapped[Restaurant] = relationship(back_populates="reports")
