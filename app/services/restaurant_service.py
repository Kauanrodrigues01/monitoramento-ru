from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.core.logging import get_logger
from app.exceptions.restaurant import (
    RestaurantAlreadyExistsError,
    RestaurantNotFoundError,
)
from app.models.restaurant import Restaurant
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.restaurants import RestaurantCreate, RestaurantUpdate

logger = get_logger(__name__)


class RestaurantService:
    def __init__(self, repo: RestaurantRepository):
        self.repo = repo

    async def create_restaurant(self, restaurant_data: RestaurantCreate) -> Restaurant:
        existing = await self.repo.get_by_name(restaurant_data.name)
        if existing:
            logger.warning(
                "Tentativa de criar restaurante duplicado: %s", restaurant_data.name
            )
            raise RestaurantAlreadyExistsError()

        try:
            restaurant = Restaurant(**restaurant_data.model_dump())
            await self.repo.create(restaurant)
            await self.repo.db_session.commit()
            logger.info(
                "Restaurante criado: %s (campus: %s)",
                restaurant.name,
                restaurant.campus.value,
            )
            return restaurant

        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantAlreadyExistsError()

        except Exception:
            await self.repo.db_session.rollback()
            raise

    async def list_restaurants(self) -> list[Restaurant]:
        restaurants = await self.repo.get_all()
        return restaurants

    async def get_restaurant(self, public_id: UUID) -> Restaurant:
        restaurant = await self.repo.get_by_public_id(public_id)

        if not restaurant:
            logger.warning("Restaurante não encontrado: %s", public_id)
            raise RestaurantNotFoundError()

        return restaurant

    async def update_restaurant(
        self,
        public_id: UUID,
        restaurant_data: RestaurantUpdate,
    ) -> Restaurant:
        restaurant = await self.repo.get_by_public_id(public_id)

        if not restaurant:
            raise RestaurantNotFoundError()

        updated_data = restaurant_data.model_dump(
            exclude_unset=True,
            exclude_none=True,
        )

        new_name = updated_data.get("name")

        if new_name and new_name != restaurant.name:
            existing = await self.repo.get_by_name(new_name)

            if existing:
                raise RestaurantAlreadyExistsError()

        for field, value in updated_data.items():
            setattr(
                restaurant,
                field,
                value,
            )

        try:
            await self.repo.db_session.commit()
            await self.repo.db_session.refresh(restaurant)
            return restaurant

        except IntegrityError:
            await self.repo.db_session.rollback()
            raise RestaurantAlreadyExistsError()

        except Exception:
            await self.repo.db_session.rollback()
            raise
