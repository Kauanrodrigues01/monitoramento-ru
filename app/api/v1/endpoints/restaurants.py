from uuid import UUID

from fastapi import APIRouter, Depends, Request

from app.core.openapi_responses import (
    INTERNAL_SERVER_ERROR_RESPONSE,
    RATE_LIMIT_RESPONSE,
    error_response,
)
from app.core.rate_limiter import limiter
from app.dependencies.auth import require_admin_api_key
from app.dependencies.restaurant_dependencies import RestaurantServiceDep
from app.exceptions.auth import InvalidAdminApiKeyError
from app.exceptions.restaurant_exceptions import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
)
from app.schemas.restaurant_schemas import (
    RestaurantCreate,
    RestaurantResponse,
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
    responses=RATE_LIMIT_RESPONSE | INTERNAL_SERVER_ERROR_RESPONSE,
)
@limiter.limit("60/minute")
async def list_restaurants(request: Request, service: RestaurantServiceDep):
    return await service.list_restaurants()


@router.get(
    "/{public_id}",
    response_model=RestaurantResponse,
    responses=(
        error_response(RestaurantNotFoundError)
        | RATE_LIMIT_RESPONSE
        | INTERNAL_SERVER_ERROR_RESPONSE
    ),
)
@limiter.limit("60/minute")
async def get_restaurant(
    public_id: UUID, request: Request, service: RestaurantServiceDep
):
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
