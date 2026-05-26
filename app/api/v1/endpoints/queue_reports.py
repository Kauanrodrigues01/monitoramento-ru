from uuid import UUID

from fastapi import APIRouter, Request

from app.core.openapi_responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    RATE_LIMIT_RESPONSE,
    error_response,
)
from app.core.rate_limiter import limiter
from app.core.rate_limits import QUEUE_REPORT_RATE_LIMIT
from app.dependencies.queue_report_dependencies import QueueReportServiceDep
from app.exceptions.geo_signature_exceptions import (
    ExpiredGeoSignatureException,
    InvalidGeoSignatureException,
)
from app.exceptions.queue_report_exceptions import (
    QueueReportLocationOutOfGeofenceError,
    QueueReportOutsideMealHoursError,
    QueueReportTooRecentError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.schemas.queue_report_schemas import QueueReportCreate, QueueReportResponse
from app.services.ip_service import IpService

router = APIRouter(prefix="/restaurants", tags=["Queue Reports"])


@router.post(
    "/{restaurant_public_id}/queue-reports",
    response_model=QueueReportResponse,
    status_code=201,
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(InvalidGeoSignatureException)
        | error_response(ExpiredGeoSignatureException)
        | error_response(QueueReportLocationOutOfGeofenceError)
        | error_response(QueueReportOutsideMealHoursError)
        | error_response(QueueReportTooRecentError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit(QUEUE_REPORT_RATE_LIMIT)  # Proteção contra DoS bruto; cooldown real é feito no service
async def create_queue_report(
    restaurant_public_id: UUID,
    queue_report_data: QueueReportCreate,
    service: QueueReportServiceDep,
    request: Request,
):
    ip = IpService.get_client_ip(request)
    return await service.create_queue_report(
        restaurant_public_id, queue_report_data, ip
    )
