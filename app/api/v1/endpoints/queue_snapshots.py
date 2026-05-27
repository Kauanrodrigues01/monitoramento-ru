from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from app.core.openapi_responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    RATE_LIMIT_RESPONSE,
    error_response,
)
from app.core.rate_limiter import limiter
from app.core.rate_limits import BULK_READ_RATE_LIMIT, READ_RATE_LIMIT
from app.dependencies.queue_snapshot_dependencies import QueueSnapshotServiceDep
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_snapshot_exceptions import (
    QueueSnapshotBulkLimitExceededError,
    QueueSnapshotNotFoundError,
)
from app.services.queue_snapshot_service import BULK_LIMIT
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.schemas.queue_snapshot_schemas import QueueSnapshotBulkItem, QueueSnapshotResponse

router = APIRouter(prefix="/restaurants", tags=["Queue Snapshots"])


def _parse_public_ids(ids_str: str) -> list[UUID]:
    parts = [p.strip() for p in ids_str.split(",") if p.strip()]
    if not parts:
        raise HTTPException(status_code=422, detail="O parâmetro 'ids' não pode estar vazio.")
    try:
        return [UUID(p) for p in parts]
    except ValueError:
        raise HTTPException(status_code=422, detail="Um ou mais IDs informados são inválidos.")


@router.get(
    "/status/bulk",
    response_model=list[QueueSnapshotBulkItem],
    responses=(
        error_response(QueueSnapshotBulkLimitExceededError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(BULK_READ_RATE_LIMIT)
async def get_bulk_restaurant_status(
    request: Request,
    service: QueueSnapshotServiceDep,
    ids: str = Query(
        description=(
            f"IDs públicos dos restaurantes separados por vírgula. Máximo {BULK_LIMIT}. "
            "Ex: `?ids=uuid1,uuid2,uuid3`"
        ),
    ),
):
    public_ids = _parse_public_ids(ids)
    return await service.get_bulk_status(public_ids)


@router.get(
    "/{restaurant_public_id}/status",
    response_model=QueueSnapshotResponse,
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(QueueSnapshotNotFoundError)
        | error_response(MealPeriodClosedError)
        | error_response(OutsideMealHoursError)
        | error_response(RestaurantClosedAllDayError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(READ_RATE_LIMIT)
async def get_restaurant_status(
    restaurant_public_id: UUID, request: Request, service: QueueSnapshotServiceDep
):
    return await service.get_status(restaurant_public_id)
