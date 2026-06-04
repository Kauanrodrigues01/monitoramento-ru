from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Request

from app.core.openapi_responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    RATE_LIMIT_RESPONSE,
    error_response,
    rate_limit_with_cooldown_response,
)
from app.core.rate_limiter import limiter
from app.core.rate_limits import QUEUE_REPORT_RATE_LIMIT, READ_RATE_LIMIT
from app.dependencies.headers import DeviceIdHeaderDep
from app.dependencies.queue_report_dependencies import QueueReportServiceDep
from app.exceptions.geo_signature_exceptions import (
    ExpiredGeoSignatureException,
    InvalidGeoSignatureException,
)
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_report_exceptions import (
    QueueReportLocationOutOfGeofenceError,
    QueueReportTooRecentError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.schemas.queue_report_schemas import QueueReportCreate, QueueReportResponse
from app.services.ip_service import IpService

router = APIRouter(prefix="/restaurants", tags=["Queue Reports"])


@router.post(
    "/{restaurant_public_id}/reports",
    response_model=QueueReportResponse,
    status_code=201,
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(InvalidGeoSignatureException)
        | error_response(ExpiredGeoSignatureException)
        | error_response(QueueReportLocationOutOfGeofenceError)
        | error_response(RestaurantClosedAllDayError)
        | error_response(MealPeriodClosedError)
        | error_response(OutsideMealHoursError)
        | rate_limit_with_cooldown_response(QueueReportTooRecentError)
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(
    QUEUE_REPORT_RATE_LIMIT
)  # Proteção contra DoS bruto; cooldown real é feito no service
async def create_queue_report(
    restaurant_public_id: UUID,
    queue_report_data: QueueReportCreate,
    service: QueueReportServiceDep,
    device_id: DeviceIdHeaderDep,
    request: Request,
    background_tasks: BackgroundTasks,
):
    ip = IpService.get_client_ip(request)
    return await service.create_queue_report(
        restaurant_public_id, queue_report_data, ip, device_id, background_tasks
    )


@router.get(
    "/{restaurant_public_id}/reports/recent",
    response_model=list[QueueReportResponse],
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(RestaurantClosedAllDayError)
        | error_response(OutsideMealHoursError)
        | error_response(MealPeriodClosedError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(READ_RATE_LIMIT)
async def list_recent_queue_reports(
    restaurant_public_id: UUID,
    request: Request,
    service: QueueReportServiceDep,
):
    return await service.list_recent_queue_reports(restaurant_public_id)
