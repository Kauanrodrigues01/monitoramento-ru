from uuid import UUID

from dependencies.restaurant import RestaurantServiceDep
from fastapi import APIRouter
from schemas.restaurants import RestaurantCreate, RestaurantResponse, RestaurantUpdate

router = APIRouter(prefix="/restaurants", tags=["Restaurants"])


@router.post("/", response_model=RestaurantResponse, status_code=201)
async def create_restaurant(
    restaurant_data: RestaurantCreate, service: RestaurantServiceDep
):
    return await service.create_restaurant(restaurant_data)


@router.get("/", response_model=list[RestaurantResponse])
async def list_restaurants(service: RestaurantServiceDep):
    return await service.list_restaurants()


@router.get("/{public_id}", response_model=RestaurantResponse)
async def get_restaurant(public_id: UUID, service: RestaurantServiceDep):
    return await service.get_restaurant(public_id)


@router.patch("/{public_id}", response_model=RestaurantResponse)
async def update_restaurant(
    public_id: UUID,
    restaurant_data: RestaurantUpdate,
    service: RestaurantServiceDep
):
    return await service.update_restaurant(public_id, restaurant_data)
