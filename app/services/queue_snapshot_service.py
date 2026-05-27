from datetime import datetime
from uuid import UUID

from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_snapshot_exceptions import (
    QueueSnapshotBulkLimitExceededError,
    QueueSnapshotNotFoundError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_snapshot import QueueSnapshot
from app.models.restaurant import MealPeriodEnum, Restaurant
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.queue_snapshot_schemas import QueueSnapshotBulkItem
from app.services.meal_period_service import MealPeriodService

BULK_LIMIT = 10


class QueueSnapshotService:
    def __init__(
        self,
        repo: QueueSnapshotRepository,
        restaurant_repo: RestaurantRepository,
        meal_period_service: MealPeriodService,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo
        self.meal_period_service = meal_period_service

    async def _get_restaurant_by_public_id_or_error(
        self, public_id: UUID
    ) -> Restaurant:
        restaurant = await self.restaurant_repo.get_by_public_id(public_id)

        if not restaurant:
            raise RestaurantNotFoundError()

        return restaurant

    async def get_status(self, restaurant_public_id: UUID) -> QueueSnapshot:
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        dt = datetime.now()

        meal_period = await self.meal_period_service.resolve(ru_id=restaurant.id, at=dt)

        snapshot = await self.repo.get_by_ru_id_and_meal_period(
            ru_id=restaurant.id, meal_period=meal_period
        )

        if not snapshot:
            raise QueueSnapshotNotFoundError()

        return snapshot

    async def get_bulk_status(
        self, public_ids: list[UUID]
    ) -> list[QueueSnapshotBulkItem]:
        if len(public_ids) > BULK_LIMIT:
            raise QueueSnapshotBulkLimitExceededError()

        restaurants = await self.restaurant_repo.get_bulk_by_public_ids(public_ids)
        if not restaurants:
            return []

        dt = datetime.now()

        # resolve meal_period por restaurante; pula fechados/fora de horário
        period_groups: dict[MealPeriodEnum, list[Restaurant]] = {}
        for restaurant in restaurants:
            try:
                period = await self.meal_period_service.resolve(
                    ru_id=restaurant.id, at=dt
                )
                period_groups.setdefault(period, []).append(restaurant)
            except (RestaurantClosedAllDayError, OutsideMealHoursError, MealPeriodClosedError):
                continue

        if not period_groups:
            return []

        results: list[QueueSnapshotBulkItem] = []
        for meal_period, group in period_groups.items():
            ru_map = {r.id: r for r in group}
            snapshots = await self.repo.get_bulk_by_ru_ids_and_meal_period(
                list(ru_map.keys()), meal_period
            )
            for snapshot in snapshots:
                restaurant = ru_map[snapshot.ru_id]
                results.append(
                    QueueSnapshotBulkItem(
                        restaurant_public_id=restaurant.public_id,
                        meal_period=snapshot.meal_period,
                        current_status=snapshot.current_status,
                        reports_last_15m=snapshot.reports_last_15m,
                        last_report_at=snapshot.last_report_at,
                        updated_at=snapshot.updated_at,
                    )
                )

        return results
