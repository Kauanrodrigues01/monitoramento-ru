from decimal import Decimal

import factory

from app.models.queue_reports import QueueReport, ReportStatusEnum
from app.models.restaurant import MealPeriodEnum


class BaseQueueReportFactory(factory.Factory):
    class Meta:
        model = QueueReport

    ru_id = 1
    status = ReportStatusEnum.SMALL
    meal_period = MealPeriodEnum.LUNCH

    lat = Decimal("-4.215432")
    lng = Decimal("-38.727981")

    ip_hash = "a" * 64
    device_hash = "b" * 64

    accuracy_m = None
    confidence_score = Decimal("1.00")
    is_mock_location = False
