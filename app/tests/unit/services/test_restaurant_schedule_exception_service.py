from datetime import date, time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.exceptions.restaurant_exceptions import (
    RestaurantNotFoundError,
    RestaurantScheduleExceptionAlreadyExistsError,
    RestaurantScheduleExceptionInvalidStateError,
    RestaurantScheduleExceptionNotFoundError,
)
from app.models.restaurant import ExceptionTypeEnum, MealPeriodEnum
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.services.restaurant_schedule_exception_service import (
    RestaurantScheduleExceptionService,
)
from app.tests.factories.restaurant_model_factory import (
    RestaurantFactory,
    RestaurantScheduleExceptionFactory,
)
from app.tests.factories.restaurant_schema_factory import (
    build_restaurant_schedule_exception_create_schema,
    build_restaurant_schedule_exception_update_schema,
)


@pytest.fixture
def mock_exception_repository():
    mock = AsyncMock(spec=RestaurantScheduleExceptionRepository)
    mock.db_session = AsyncMock()
    return mock


@pytest.fixture
def mock_restaurant_repository():
    return AsyncMock(spec=RestaurantRepository)


@pytest.fixture
def service(mock_exception_repository, mock_restaurant_repository):
    return RestaurantScheduleExceptionService(
        repo=mock_exception_repository,
        restaurant_repo=mock_restaurant_repository,
    )


# ===== CREATE RESTAURANT SCHEDULE EXCEPTION =====
class TestCreateRestaurantScheduleException:
    @pytest.mark.asyncio
    async def test_should_create_exception_successfully(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema()
        created_exception = RestaurantScheduleExceptionFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = None
        mock_exception_repository.create.return_value = created_exception
        mock_exception_repository.db_session.commit = AsyncMock()

        result = await service.create_restaurant_schedule_exception(
            restaurant.public_id, exception_data
        )

        assert result.ru_id == restaurant.id
        mock_exception_repository.create.assert_called_once()
        mock_exception_repository.db_session.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_create_exception_with_correct_ru_id(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build(id=42)
        exception_data = build_restaurant_schedule_exception_create_schema()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = None
        mock_exception_repository.db_session.commit = AsyncMock()

        await service.create_restaurant_schedule_exception(
            restaurant.public_id, exception_data
        )

        called_exception = mock_exception_repository.create.call_args[0][0]
        assert called_exception.ru_id == 42

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found_on_create(
        self, service, mock_restaurant_repository
    ):
        mock_restaurant_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.create_restaurant_schedule_exception(
                uuid4(), build_restaurant_schedule_exception_create_schema()
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_exception_already_exists(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema()
        existing = RestaurantScheduleExceptionFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = existing

        with pytest.raises(RestaurantScheduleExceptionAlreadyExistsError):
            await service.create_restaurant_schedule_exception(
                restaurant.public_id, exception_data
            )

    @pytest.mark.asyncio
    async def test_should_not_call_create_when_duplicate_found(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema()
        existing = RestaurantScheduleExceptionFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = existing

        with pytest.raises(RestaurantScheduleExceptionAlreadyExistsError):
            await service.create_restaurant_schedule_exception(
                restaurant.public_id, exception_data
            )

        mock_exception_repository.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_check_duplicate_with_correct_args(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema(
            exception_date=date(2025, 6, 15),
            meal_period=MealPeriodEnum.LUNCH,
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = None
        mock_exception_repository.db_session.commit = AsyncMock()

        await service.create_restaurant_schedule_exception(
            restaurant.public_id, exception_data
        )

        mock_exception_repository.get_by_ru_id_date_and_meal_period.assert_called_once_with(
            ru_id=restaurant.id,
            exception_date=date(2025, 6, 15),
            meal_period=MealPeriodEnum.LUNCH,
        )

    @pytest.mark.asyncio
    async def test_should_log_warning_on_duplicate_exception(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema()
        existing = RestaurantScheduleExceptionFactory.build(ru_id=restaurant.id)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = existing

        with patch(
            "app.services.restaurant_schedule_exception_service.logger"
        ) as mock_logger:
            with pytest.raises(RestaurantScheduleExceptionAlreadyExistsError):
                await service.create_restaurant_schedule_exception(
                    restaurant.public_id, exception_data
                )

            mock_logger.warning.assert_called_once()
            assert "duplicada" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_should_rollback_on_integrity_error_during_create(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = None
        mock_exception_repository.create.side_effect = IntegrityError("", "", "")
        mock_exception_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantScheduleExceptionAlreadyExistsError):
            await service.create_restaurant_schedule_exception(
                restaurant.public_id, exception_data
            )

        mock_exception_repository.db_session.rollback.assert_called_once()
        mock_exception_repository.db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_and_reraise_unexpected_error_during_create(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception_data = build_restaurant_schedule_exception_create_schema()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_ru_id_date_and_meal_period.return_value = None
        mock_exception_repository.create.side_effect = RuntimeError("Erro inesperado")
        mock_exception_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RuntimeError):
            await service.create_restaurant_schedule_exception(
                restaurant.public_id, exception_data
            )

        mock_exception_repository.db_session.rollback.assert_called_once()


# ===== LIST RESTAURANT SCHEDULE EXCEPTIONS =====
class TestListRestaurantScheduleExceptions:
    @pytest.mark.asyncio
    async def test_should_list_all_exceptions_when_no_date_filter(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exceptions = [
            RestaurantScheduleExceptionFactory.build(ru_id=restaurant.id),
            RestaurantScheduleExceptionFactory.build(ru_id=restaurant.id),
        ]

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.list_by_ru_id.return_value = exceptions

        result = await service.list_restaurant_schedule_exceptions(
            restaurant.public_id, None
        )

        assert len(result) == 2
        mock_exception_repository.list_by_ru_id.assert_called_once_with(restaurant.id)
        mock_exception_repository.list_by_ru_id_and_date.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_filter_by_date_when_provided(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        target_date = date(2025, 12, 25)
        exceptions = [
            RestaurantScheduleExceptionFactory.build(
                ru_id=restaurant.id, exception_date=target_date
            ),
        ]

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.list_by_ru_id_and_date.return_value = exceptions

        result = await service.list_restaurant_schedule_exceptions(
            restaurant.public_id, target_date
        )

        assert len(result) == 1
        mock_exception_repository.list_by_ru_id_and_date.assert_called_once_with(
            restaurant.id, target_date
        )
        mock_exception_repository.list_by_ru_id.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_return_empty_list_when_no_exceptions(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.list_by_ru_id.return_value = []

        result = await service.list_restaurant_schedule_exceptions(
            restaurant.public_id, None
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found_on_list(
        self, service, mock_restaurant_repository
    ):
        mock_restaurant_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.list_restaurant_schedule_exceptions(uuid4(), None)


# ===== UPDATE RESTAURANT SCHEDULE EXCEPTION =====
class TestUpdateRestaurantScheduleException:
    @pytest.mark.asyncio
    async def test_should_update_exception_successfully(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_exception_update_schema(
            opens_at=time(10, 0)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception
        mock_exception_repository.db_session.commit = AsyncMock()
        mock_exception_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant_schedule_exception(
            restaurant.public_id, exception.public_id, update_data
        )

        assert result.opens_at == time(10, 0)
        mock_exception_repository.db_session.commit.assert_called_once()
        mock_exception_repository.db_session.refresh.assert_called_once_with(exception)

    @pytest.mark.asyncio
    async def test_should_preserve_existing_fields_on_partial_update(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            meal_period=MealPeriodEnum.LUNCH,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
            reason="Horário reduzido",
        )
        update_data = build_restaurant_schedule_exception_update_schema(
            opens_at=time(10, 30)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception
        mock_exception_repository.db_session.commit = AsyncMock()
        mock_exception_repository.db_session.refresh = AsyncMock()

        result = await service.update_restaurant_schedule_exception(
            restaurant.public_id, exception.public_id, update_data
        )

        assert result.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        assert result.meal_period == MealPeriodEnum.LUNCH
        assert result.closes_at == time(14, 0)
        assert result.reason == "Horário reduzido"

    @pytest.mark.asyncio
    async def test_should_raise_error_when_restaurant_not_found_on_update(
        self, service, mock_restaurant_repository
    ):
        mock_restaurant_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.update_restaurant_schedule_exception(
                uuid4(),
                uuid4(),
                build_restaurant_schedule_exception_update_schema(),
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_exception_not_found(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = None

        with pytest.raises(RestaurantScheduleExceptionNotFoundError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id,
                uuid4(),
                build_restaurant_schedule_exception_update_schema(),
            )

    @pytest.mark.asyncio
    async def test_should_raise_error_when_exception_belongs_to_different_restaurant(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build(id=1)
        other_exception = RestaurantScheduleExceptionFactory.build(ru_id=99)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = other_exception

        with pytest.raises(RestaurantScheduleExceptionNotFoundError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id,
                other_exception.public_id,
                build_restaurant_schedule_exception_update_schema(),
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_custom_hours_missing_opens_at(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        # patch removes opens_at, leaving state invalid
        update_data = build_restaurant_schedule_exception_update_schema(opens_at=None)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_custom_hours_missing_closes_at(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_exception_update_schema(closes_at=None)

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_custom_hours_opens_at_equals_closes_at(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_exception_update_schema(
            closes_at=time(11, 0)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_custom_hours_opens_at_after_closes_at(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        # existing opens_at=11:00, patch closes_at=10:00 → inválido
        update_data = build_restaurant_schedule_exception_update_schema(
            closes_at=time(10, 0)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_closed_with_opens_at(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CLOSED,
            opens_at=None,
            closes_at=None,
        )
        update_data = build_restaurant_schedule_exception_update_schema(
            opens_at=time(11, 0)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_closed_with_closes_at(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CLOSED,
            opens_at=None,
            closes_at=None,
        )
        update_data = build_restaurant_schedule_exception_update_schema(
            closes_at=time(14, 0)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_raise_invalid_state_when_switching_to_closed_with_existing_times(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        # muda só o tipo para CLOSED sem limpar os horários
        update_data = build_restaurant_schedule_exception_update_schema(
            exception_type=ExceptionTypeEnum.CLOSED,
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

    @pytest.mark.asyncio
    async def test_should_not_commit_when_state_is_invalid(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_exception_update_schema(
            closes_at=time(10, 0)
        )

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception
        mock_exception_repository.db_session.commit = AsyncMock()

        with pytest.raises(RestaurantScheduleExceptionInvalidStateError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

        mock_exception_repository.db_session.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_rollback_on_integrity_error_during_update(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_exception_update_schema(reason="Greve")

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception
        mock_exception_repository.db_session.commit.side_effect = IntegrityError(
            "", "", ""
        )
        mock_exception_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RestaurantScheduleExceptionAlreadyExistsError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

        mock_exception_repository.db_session.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_rollback_and_reraise_unexpected_error_during_update(
        self, service, mock_exception_repository, mock_restaurant_repository
    ):
        restaurant = RestaurantFactory.build()
        exception = RestaurantScheduleExceptionFactory.build(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        update_data = build_restaurant_schedule_exception_update_schema(reason="Greve")

        mock_restaurant_repository.get_by_public_id.return_value = restaurant
        mock_exception_repository.get_by_public_id.return_value = exception
        mock_exception_repository.db_session.commit.side_effect = RuntimeError("Erro BD")
        mock_exception_repository.db_session.rollback = AsyncMock()

        with pytest.raises(RuntimeError):
            await service.update_restaurant_schedule_exception(
                restaurant.public_id, exception.public_id, update_data
            )

        mock_exception_repository.db_session.rollback.assert_called_once()
