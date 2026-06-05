from uuid import UUID

from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.restaurant import Restaurant
from app.repositories.restaurant_repository import RestaurantRepository


class RestaurantResolverMixin:
    restaurant_repo: RestaurantRepository

    async def _get_restaurant_by_public_id_or_error(
        self, public_id: UUID
    ) -> Restaurant:
        restaurant = await self.restaurant_repo.get_by_public_id(public_id)

        if restaurant is None:
            raise RestaurantNotFoundError()

        return restaurant
