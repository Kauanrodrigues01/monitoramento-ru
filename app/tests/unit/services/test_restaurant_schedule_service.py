from datetime import time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.restaurant_exceptions import (
    RestaurantNotFoundError,
    RestaurantScheduleAlreadyExistsError,
    RestaurantScheduleNotFoundError,
    RestaurantScheduleOpensBeforeClosesError,
)
from app.models.restaurant import MealPeriodEnum
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.restaurant_schedule_service import RestaurantScheduleService
from app.tests.factories.models.unit.restaurant_model_factory import (
    RestaurantFactory,
    RestaurantScheduleFactory,
)
from app.tests.factories.schemas.restaurant_schema_factory import (
    build_restaurant_schedule_create_schema,
    build_restaurant_schedule_update_schema,
)


@pytest.fixture
def mock_schedule_repository():
    mock = AsyncMock(spec=RestaurantScheduleRepository)
    mock.db_session = AsyncMock()
    return mock


@pytest.fixture
def mock_restaurant_repository():
    return AsyncMock(spec=RestaurantRepository)


@pytest.fixture
def service(mock_schedule_repository, mock_restaurant_repository):
    return RestaurantScheduleService(
        repo=mock_schedule_repository,
        restaurant_repo=mock_restaurant_repository,
    )


# ===== CREATE RESTAURANT SCHEDULE =====
class TestCreateRestaurantSchedule:
    @pytest.mark.asyncio
    async def test_should_create_schedule_successfully(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule_data = build_restaurant_schedule_create_schema()
        created_schedule = RestaurantScheduleFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            None
        )
        mock_schedule_repository.create.return_value = created_schedule
        mock_schedule_repository.db_session.commit = AsyncMock()

        result = await service.create_restaurant_schedule(
            restaurant.public_id, schedule_data
        )

        assert result.ru_id == restaurant.id
        mock_schedule_repository.create.assert_called_once()
        mock_schedule_repository.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_schedule_with_correct_ru_id(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build(id=42)
        schedule_data = build_restaurant_schedule_create_schema()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            None
        )
        mock_schedule_repository.db_session.commit = AsyncMock()

        await service.create_restaurant_schedule(restaurant.public_id, schedule_data)

        called_schedule = mock_schedule_repository.create.call_args[0][0]
        assert called_schedule.ru_id == 42

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found_on_create(
        self, service, mock_restaurant_repository
    ):
        mock_restaurant_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.create_restaurant_schedule(
                uuid4(), build_restaurant_schedule_create_schema()
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_schedule_already_exists(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule_data = build_restaurant_schedule_create_schema()
        existing_schedule = RestaurantScheduleFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            existing_schedule
        )

        with pytest.raises(RestaurantScheduleAlreadyExistsError):
            await service.create_restaurant_schedule(
                restaurant.public_id, schedule_data
            )

        mock_schedule_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_on_integrity_error_during_create(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule_data = build_restaurant_schedule_create_schema()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            None
        )
        mock_schedule_repository.create.side_effect = IntegrityError("", "", "")
        mock_schedule_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantScheduleAlreadyExistsError):
            await service.create_restaurant_schedule(
                restaurant.public_id, schedule_data
            )

        mock_schedule_repository.db_session.rollback.assert_called_once()
        mock_schedule_repository.db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_and_reraise_unexpected_error_during_create(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule_data = build_restaurant_schedule_create_schema()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            None
        )
        mock_schedule_repository.create.side_effect = RuntimeError("Erro inesperado")
        mock_schedule_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RuntimeError):
            await service.create_restaurant_schedule(
                restaurant.public_id, schedule_data
            )

        mock_schedule_repository.db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_check_duplicate_with_correct_args(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule_data = build_restaurant_schedule_create_schema(
            weekday=3, meal_period=MealPeriodEnum.DINNER
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            None
        )
        mock_schedule_repository.db_session.commit = AsyncMock()

        await service.create_restaurant_schedule(restaurant.public_id, schedule_data)

        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.assert_called_once_with(
            ru_id=restaurant.id,
            weekday=3,
            meal_period=MealPeriodEnum.DINNER,
        )

    @pytest.mark.asyncio
    async def test_should_log_warning_on_duplicate_schedule(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule_data = build_restaurant_schedule_create_schema()
        existing_schedule = RestaurantScheduleFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_ru_id_weekday_and_meal_period.return_value = (
            existing_schedule
        )

        with patch("app.services.restaurant_schedule_service.logger") as mock_logger:
            with pytest.raises(RestaurantScheduleAlreadyExistsError):
                await service.create_restaurant_schedule(
                    restaurant.public_id, schedule_data
                )

            mock_logger.warning.assert_called_once()
            assert "duplicado" in mock_logger.warning.call_args[0][0]


# ===== LIST RESTAURANT SCHEDULES =====
class TestListRestaurantSchedules:
    @pytest.mark.asyncio
    async def test_should_list_all_schedules_when_no_filter(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedules = [
            RestaurantScheduleFactory.build(ru_id=restaurant.id, weekday=0),
            RestaurantScheduleFactory.build(ru_id=restaurant.id, weekday=1),
        ]

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.list_by_ru_id.return_value = schedules

        result = await service.list_restaurant_schedules(restaurant.public_id, None)

        assert len(result) == 2
        mock_schedule_repository.list_by_ru_id.assert_called_once_with(restaurant.id)
        mock_schedule_repository.list_by_ru_id_and_meal_period.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_filter_by_meal_period_when_provided(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        lunch_schedules = [
            RestaurantScheduleFactory.build(
                ru_id=restaurant.id, meal_period=MealPeriodEnum.LUNCH
            ),
        ]

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.list_by_ru_id_and_meal_period.return_value = (
            lunch_schedules
        )

        result = await service.list_restaurant_schedules(
            restaurant.public_id, MealPeriodEnum.LUNCH
        )

        assert len(result) == 1
        mock_schedule_repository.list_by_ru_id_and_meal_period.assert_called_once_with(
            restaurant.id, MealPeriodEnum.LUNCH
        )
        mock_schedule_repository.list_by_ru_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_schedules(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.list_by_ru_id.return_value = []

        result = await service.list_restaurant_schedules(restaurant.public_id, None)

        assert result == []

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found_on_list(
        self, service, mock_restaurant_repository
    ):
        mock_restaurant_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.list_restaurant_schedules(uuid4(), None)


# ===== UPDATE RESTAURANT SCHEDULE =====
class TestUpdateRestaurantSchedule:
    @pytest.mark.asyncio
    async def test_should_update_schedule_successfully(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule = RestaurantScheduleFactory.build(
            ru_id=restaurant.id,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_update_schema(opens_at=time(10, 0))

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = schedule
        mock_schedule_repository.db_session.commit = AsyncMock()
        mock_schedule_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant_schedule(
            restaurant.public_id, schedule.public_id, update_data
        )

        assert result.opens_at == time(10, 0)
        mock_schedule_repository.db_session.commit.assert_called_once()
        mock_schedule_repository.db_session.refresh.assert_called_once_with(schedule)

    @pytest.mark.asyncio
    async def test_should_preserve_existing_fields_on_partial_update(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule = RestaurantScheduleFactory.build(
            ru_id=restaurant.id,
            weekday=2,
            meal_period=MealPeriodEnum.LUNCH,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
            is_active=True,
        )
        update_data = build_restaurant_schedule_update_schema(opens_at=time(10, 30))

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = schedule
        mock_schedule_repository.db_session.commit = AsyncMock()
        mock_schedule_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant_schedule(
            restaurant.public_id, schedule.public_id, update_data
        )

        assert result.weekday == 2
        assert result.meal_period == MealPeriodEnum.LUNCH
        assert result.closes_at == time(14, 0)
        assert result.is_active is True

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found_on_update(
        self, service, mock_restaurant_repository
    ):
        mock_restaurant_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.update_restaurant_schedule(
                uuid4(), uuid4(), build_restaurant_schedule_update_schema()
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_schedule_not_found(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantScheduleNotFoundError):
            await service.update_restaurant_schedule(
                restaurant.public_id, uuid4(), build_restaurant_schedule_update_schema()
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_schedule_belongs_to_different_restaurant(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build(id=1)
        other_restaurant_schedule = RestaurantScheduleFactory.build(ru_id=99)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = (
            other_restaurant_schedule
        )

        with pytest.raises(RestaurantScheduleNotFoundError):
            await service.update_restaurant_schedule(
                restaurant.public_id,
                other_restaurant_schedule.public_id,
                build_restaurant_schedule_update_schema(),
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_partial_update_results_in_invalid_time_range(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule = RestaurantScheduleFactory.build(
            ru_id=restaurant.id,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        # envia só closes_at menor que o opens_at já existente no banco
        update_data = build_restaurant_schedule_update_schema(closes_at=time(10, 0))

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = schedule

        with pytest.raises(RestaurantScheduleOpensBeforeClosesError):
            await service.update_restaurant_schedule(
                restaurant.public_id, schedule.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_not_commit_when_time_range_is_invalid(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule = RestaurantScheduleFactory.build(
            ru_id=restaurant.id,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_update_schema(closes_at=time(10, 0))

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = schedule
        mock_schedule_repository.db_session.commit = AsyncMock()

        with pytest.raises(RestaurantScheduleOpensBeforeClosesError):
            await service.update_restaurant_schedule(
                restaurant.public_id, schedule.public_id, update_data
            )

        mock_schedule_repository.db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_on_integrity_error_during_update(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule = RestaurantScheduleFactory.build(
            ru_id=restaurant.id,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_update_schema(weekday=3)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = schedule
        mock_schedule_repository.db_session.commit.side_effect = IntegrityError(
            "", "", ""
        )
        mock_schedule_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantScheduleAlreadyExistsError):
            await service.update_restaurant_schedule(
                restaurant.public_id, schedule.public_id, update_data
            )

        mock_schedule_repository.db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_rollback_and_reraise_unexpected_error_during_update(
        self, service, mock_schedule_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        schedule = RestaurantScheduleFactory.build(
            ru_id=restaurant.id,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_update_schema(weekday=3)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_schedule_repository.get_by_public_id.return_value = schedule
        mock_schedule_repository.db_session.commit.side_effect = RuntimeError("Erro BD")
        mock_schedule_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RuntimeError):
            await service.update_restaurant_schedule(
                restaurant.public_id, schedule.public_id, update_data
            )

        mock_schedule_repository.db_session.rollback.assert_called_once()
