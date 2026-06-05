from uuid import uuid4

import pytest

from app.exceptions.restaurant_exceptions import RestaurantNotFoundError


class TestGetRestaurantByPublicIdOrError:
    async def test_restaurant_found_returns_instance(
        self, service, mock_restaurant_repo, restaurant
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        result = await service._get_restaurant_by_public_id_or_error(
            restaurant.public_id
        )

        assert result is restaurant

    async def test_restaurant_not_found_raises_restaurant_not_found_error(
        self, service, mock_restaurant_repo
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service._get_restaurant_by_public_id_or_error(uuid4())
