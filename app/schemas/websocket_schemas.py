from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum


class WebSocketResponse(BaseModel):
    type: str


class SnapshotUpdatedEvent(WebSocketResponse):
    type: str = "snapshot_updated"

    restaurant_public_id: UUID
    meal_period: MealPeriodEnum
    current_status: SnapshotStatusEnum
    reports_last_15m: int
    last_report_at: datetime | None
    confidence_score: float
    data_freshness_minutes: int | None
    updated_at: datetime
