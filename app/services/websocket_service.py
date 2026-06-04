from uuid import UUID

from app.core.datetime_utils import utc_now
from app.core.redis import get_redis
from app.schemas.websocket_schemas import SnapshotUpdatedEvent


class SnapshotWebSocketService:
    @staticmethod
    async def publish_snapshot(snapshot, restaurant_public_id: UUID) -> None:
        redis = await get_redis()

        last_report_at = snapshot.last_report_at
        freshness_min: int | None = None
        if last_report_at is not None:
            freshness_min = max(
                0,
                round((utc_now() - last_report_at).total_seconds() / 60),
            )

        event = SnapshotUpdatedEvent(
            restaurant_public_id=restaurant_public_id,
            meal_period=snapshot.meal_period,
            current_status=snapshot.current_status,
            reports_last_15m=snapshot.reports_last_15m,
            last_report_at=last_report_at,
            confidence_score=float(snapshot.confidence_score),
            data_freshness_minutes=freshness_min,
            updated_at=utc_now(),
        )

        await redis.publish("snapshots", event.model_dump_json())
