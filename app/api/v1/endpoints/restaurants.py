from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.openapi_responses import INTERNAL_SERVER_ERROR_RESPONSE, error_response
from app.dependencies.auth import require_admin_api_key
from app.dependencies.restaurant_dependencies import (
    RestaurantScheduleServiceDep,
    RestaurantServiceDep,
)
from app.exceptions.auth import InvalidAdminApiKeyError
from app.exceptions.restaurant_exceptions import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
    RestaurantScheduleAlreadyExistsError,
    RestaurantScheduleNotFoundError,
    RestaurantScheduleOpensBeforeClosesError,
)
from app.models.restaurant import MealPeriodEnum
from app.schemas.restaurant_schemas import (
    RestaurantCreate,
    RestaurantResponse,
    RestaurantScheduleCreate,
    RestaurantScheduleResponse,
    RestaurantScheduleUpdate,
    RestaurantUpdate,
)

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.post(
    "/",
    response_model=RestaurantResponse,
    status_code=201,
    dependencies=[Depends(require_admin_api_key)],
    responses=(
        error_response(RestaurantAlreadyExistsError)
        | error_response(InvalidAdminApiKeyError)
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
async def create_restaurant(
    restaurant_data: RestaurantCreate, service: RestaurantServiceDep
):
    return await service.create_restaurant(restaurant_data)


@router.get(
    "/",
    response_model=list[RestaurantResponse],
    responses=INTERNAL_SERVER_ERROR_RESPONSE,
)
async def list_restaurants(service: RestaurantServiceDep):
    return await service.list_restaurants()


@router.get(
    "/{public_id}",
    response_model=RestaurantResponse,
    responses=error_response(RestaurantNotFoundError) | INTERNAL_SERVER_ERROR_RESPONSE,
)
async def get_restaurant(public_id: UUID, service: RestaurantServiceDep):
    return await service.get_restaurant(public_id)


@router.patch(
    "/{public_id}",
    response_model=RestaurantResponse,
    dependencies=[Depends(require_admin_api_key)],
    responses=(
        error_response(RestaurantAlreadyExistsError)
        | error_response(RestaurantNotFoundError)
        | error_response(InvalidAdminApiKeyError)
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
async def update_restaurant(
    public_id: UUID, restaurant_data: RestaurantUpdate, service: RestaurantServiceDep
):
    return await service.update_restaurant(public_id, restaurant_data)


@router.post(
    "/{public_id}/schedules",
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
    public_id: UUID,
    restaurant_schedule_data: RestaurantScheduleCreate,
    service: RestaurantScheduleServiceDep,
):
    return await service.create_restaurant_schedule(public_id, restaurant_schedule_data)


@router.get(
    "/{public_id}/schedules",
    response_model=list[RestaurantScheduleResponse],
    responses=error_response(RestaurantNotFoundError) | INTERNAL_SERVER_ERROR_RESPONSE,
)
async def list_restaurant_schedules(
    public_id: UUID,
    service: RestaurantScheduleServiceDep,
    meal_period: MealPeriodEnum
    | None = None,  # Default: None, faz parametro não ser obrigatorio
):
    return await service.list_restaurant_schedules(public_id, meal_period)


@router.patch(
    "/{restaurant_public_id}/schedules/{restaurant_schedule_public_id}",
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
    restaurant_schedule_public_id: UUID,
    restaurant_schedule_data: RestaurantScheduleUpdate,
    service: RestaurantScheduleServiceDep,
):
    return await service.update_restaurant_schedule(
        restaurant_public_id, restaurant_schedule_public_id, restaurant_schedule_data
    )
