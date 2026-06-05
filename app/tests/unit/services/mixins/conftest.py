from unittest.mock import AsyncMock

import pytest

from app.repositories.restaurant_repository import RestaurantRepository
from app.services._mixins import RestaurantResolverMixin
from app.tests.factories.restaurant_model_factory import RestaurantFactory


class DummyRestaurantResolverService(RestaurantResolverMixin):
    def __init__(
        self,
        restaurant_repo: RestaurantRepository,
    ):
        self.restaurant_repo = restaurant_repo


@pytest.fixture
def restaurant():
    return RestaurantFactory.build(
        geofence_radius_m=100,
    )


@pytest.fixture
def mock_restaurant_repo():
    return AsyncMock(
        spec=RestaurantRepository,
    )


@pytest.fixture
def service(
    mock_restaurant_repo,
):
    return DummyRestaurantResolverService(
        restaurant_repo=mock_restaurant_repo,
    )
