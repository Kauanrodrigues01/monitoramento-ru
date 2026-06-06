from datetime import UTC, datetime
from uuid import uuid4

from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.schemas.queue_snapshot_schemas import QueueSnapshotBulkItem


def build_queue_snapshot_bulk_item(**kwargs) -> QueueSnapshotBulkItem:
    data: dict = {
        "restaurant_public_id": uuid4(),
        "meal_period": MealPeriodEnum.LUNCH,
        "current_status": SnapshotStatusEnum.NO_DATA,
        "reports_last_15m": 0,
        "last_report_at": None,
        "updated_at": datetime(2026, 5, 26, 11, 45, 0, tzinfo=UTC),
        "confidence_score": 1.0,
    }
    data.update(kwargs)
    return QueueSnapshotBulkItem(**data)
