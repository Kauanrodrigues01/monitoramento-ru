from fastapi import APIRouter, Request

from app.core.openapi_responses import INTERNAL_SERVER_ERROR_RESPONSE, RATE_LIMIT_RESPONSE
from app.core.rate_limiter import limiter
from app.core.rate_limits import METRICS_RATE_LIMIT
from app.dependencies.metrics_dependencies import MetricsServiceDep
from app.schemas.metrics_schemas import MetricsSummaryResponse

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/summary",
    response_model=MetricsSummaryResponse,
    responses=(RATE_LIMIT_RESPONSE | INTERNAL_SERVER_ERROR_RESPONSE),
)
@limiter.limit(METRICS_RATE_LIMIT)
async def get_metrics_summary(request: Request, service: MetricsServiceDep):
    return await service.get_summary()
