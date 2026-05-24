from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.openapi_responses import error_response
from app.dependencies.auth import require_admin_api_key
from app.dependencies.restaurant import RestaurantServiceDep
from app.exceptions.auth import InvalidAdminApiKeyError
from app.exceptions.restaurant import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
)
from app.schemas.restaurants import (
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
    ),
)
async def create_restaurant(
    restaurant_data: RestaurantCreate, service: RestaurantServiceDep
):
    return await service.create_restaurant(restaurant_data)


@router.get(
    "/",
    response_model=list[RestaurantResponse],
)
async def list_restaurants(service: RestaurantServiceDep):
    return await service.list_restaurants()


@router.get(
    "/{public_id}",
    response_model=RestaurantResponse,
    responses=error_response(RestaurantNotFoundError),
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
    ),
)
async def update_restaurant(
    public_id: UUID, restaurant_data: RestaurantUpdate, service: RestaurantServiceDep
):
    return await service.update_restaurant(public_id, restaurant_data)
