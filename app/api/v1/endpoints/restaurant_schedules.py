from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.openapi_responses import INTERNAL_SERVER_ERROR_RESPONSE, error_response
from app.dependencies.auth import require_admin_api_key
from app.dependencies.restaurant_dependencies import RestaurantScheduleServiceDep
from app.exceptions.auth import InvalidAdminApiKeyError
from app.exceptions.restaurant_exceptions import (
    RestaurantNotFoundError,
    RestaurantScheduleAlreadyExistsError,
    RestaurantScheduleNotFoundError,
    RestaurantScheduleOpensBeforeClosesError,
)
from app.models.restaurant import MealPeriodEnum
from app.schemas.restaurant_schedule_schemas import (
    RestaurantScheduleCreate,
    RestaurantScheduleResponse,
    RestaurantScheduleUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["Restaurant Schedules"])


@router.post(
    "/{restaurant_public_id}/schedules",
    status_code=201,
    response_model=RestaurantScheduleResponse,
    dependencies=[Depends(require_admin_api_key)],
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(RestaurantScheduleAlreadyExistsError)
        | error_response(InvalidAdminApiKeyError)
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
async def create_restaurant_schedule(
    restaurant_public_id: UUID,
    restaurant_schedule_data: RestaurantScheduleCreate,
    service: RestaurantScheduleServiceDep,
):
    return await service.create_restaurant_schedule(
        restaurant_public_id, restaurant_schedule_data
    )


@router.get(
    "/{restaurant_public_id}/schedules",
    response_model=list[RestaurantScheduleResponse],
    responses=error_response(RestaurantNotFoundError) | INTERNAL_SERVER_ERROR_RESPONSE,
)
async def list_restaurant_schedules(
    restaurant_public_id: UUID,
    service: RestaurantScheduleServiceDep,
    meal_period: MealPeriodEnum | None = None,
):
    return await service.list_restaurant_schedules(restaurant_public_id, meal_period)


@router.patch(
    "/{restaurant_public_id}/schedules/{schedule_public_id}",
    response_model=RestaurantScheduleResponse,
    dependencies=[Depends(require_admin_api_key)],
    responses=(
        error_response(RestaurantNotFoundError)
        | error_response(RestaurantScheduleNotFoundError)
        | error_response(RestaurantScheduleAlreadyExistsError)
        | error_response(RestaurantScheduleOpensBeforeClosesError)
        | error_response(InvalidAdminApiKeyError)
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
async def update_restaurant_schedule(
    restaurant_public_id: UUID,
    schedule_public_id: UUID,
    restaurant_schedule_data: RestaurantScheduleUpdate,
    service: RestaurantScheduleServiceDep,
):
    return await service.update_restaurant_schedule(
        restaurant_public_id, schedule_public_id, restaurant_schedule_data
    )
