from decimal import Decimal

from app.core.datetime_utils import to_app_tz, utc_now
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.models.queue_snapshot import SnapshotStatusEnum
from app.repositories.queue_report_repository import QueueReportRepository
from app.schemas.metrics_schemas import MetricsSummaryResponse
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService


class MetricsService:
    def __init__(
        self,
        snapshot_repo: QueueSnapshotRepository,
        report_repo: QueueReportRepository,
        restaurant_repo: RestaurantRepository,
        meal_period_service: MealPeriodService,
    ):
        self.snapshot_repo = snapshot_repo
        self.report_repo = report_repo
        self.restaurant_repo = restaurant_repo
        self.meal_period_service = meal_period_service

    async def get_summary(self) -> MetricsSummaryResponse:
        total_active_restaurants = await self.restaurant_repo.count_active()

        # Verifica quais restaurantes estão abertos agora via MealPeriodService
        restaurants = await self.restaurant_repo.get_all(only_active=True)
        now = to_app_tz(utc_now())
        open_now = 0
        for restaurant in restaurants:
            try:
                await self.meal_period_service.resolve(ru_id=restaurant.id, at=now)
                open_now += 1
            except (
                RestaurantClosedAllDayError,
                OutsideMealHoursError,
                MealPeriodClosedError,
            ):
                pass

        reports_last_15m = await self.report_repo.count_within_minutes(minutes=15)

        reports_today = await self.report_repo.count_today()

        all_snapshots = await self.snapshot_repo.list_all()

        status_distribution: dict[str, int] = {}
        for snap in all_snapshots:
            key = snap.current_status.value
            status_distribution[key] = status_distribution.get(key, 0) + 1

        scored_snapshots = [
            s for s in all_snapshots if s.current_status != SnapshotStatusEnum.NO_DATA
        ]
        avg_confidence: float | None = None
        if scored_snapshots:
            total = sum(s.confidence_score for s in scored_snapshots)
            avg_confidence = round(float(total / Decimal(len(scored_snapshots))), 2)

        return MetricsSummaryResponse(
            total_active_restaurants=total_active_restaurants,
            open_now=open_now,
            reports_last_15m=reports_last_15m,
            reports_today=reports_today,
            status_distribution=status_distribution,
            avg_confidence=avg_confidence,
        )
