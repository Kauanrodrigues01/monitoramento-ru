from decimal import Decimal

import factory

from app.models.queue_snapshot import (
    QueueSnapshot,
    SnapshotStatusEnum,
)
from app.models.restaurant import MealPeriodEnum


class BaseQueueSnapshotFactory(factory.Factory):
    class Meta:
        model = QueueSnapshot

    ru_id = 1

    meal_period = MealPeriodEnum.LUNCH

    current_status = SnapshotStatusEnum.NO_DATA

    avg_status_value = None

    reports_last_15m = 0

    confidence_score = Decimal("1.00")

    override_active = False

    last_report_at = None
