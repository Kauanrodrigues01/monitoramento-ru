from fastapi import Request

from app.api.v1.endpoints.queue_reports import router as queue_reports_router
from app.api.v1.endpoints.queue_snapshots import router as queue_snapshots_router
from app.api.v1.endpoints.restaurant_schedule_exceptions import (
    router as restaurant_schedule_exceptions_router,
)
from app.api.v1.endpoints.restaurant_schedules import (
    router as restaurant_schedules_router,
)
from app.api.v1.endpoints.restaurants import router as restaurants_router
from app.core.logging import get_logger
from app.core.observability.helpers import track_business_request

BUSINESS_TAGS = set().union(
    restaurants_router.tags,
    restaurant_schedule_exceptions_router.tags,
    restaurant_schedules_router.tags,
    queue_reports_router.tags,
    queue_snapshots_router.tags,
)

logger = get_logger(__name__)


async def business_metrics_middleware(
    request: Request,
    call_next,
):
    response = await call_next(request)

    route = request.scope.get("route")

    if route is None:
        return response

    route_tags = set(getattr(route, "tags", []))

    if not route_tags.intersection(BUSINESS_TAGS):
        logger.debug(
            "Business metric IGNORADA, path: %s, tags: %s",
            route.path,
            list(route_tags),
        )
        return response

    logger.debug(
        "Business metric CONTABILIZADA, path: %s, tags: %s",
        route.path,
        list(route_tags),
    )

    track_business_request(
        endpoint=route.path,
        method=request.method,
        status_code=response.status_code,
    )

    return response
