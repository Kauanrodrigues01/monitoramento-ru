from datetime import datetime, time
from unittest.mock import AsyncMock

import pytest

from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.models.restaurant import ExceptionTypeEnum, MealPeriodEnum
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.services.meal_period_service import MealPeriodService
from app.tests.factories.restaurant_model_factory import (
    RestaurantScheduleExceptionFactory,
    RestaurantScheduleFactory,
)

_RU_ID = 1

# segunda-feira (weekday=0)
_AT_LUNCH = datetime(2026, 5, 25, 12, 0)   # 12h — dentro do almoço (11–14h)
_AT_DINNER = datetime(2026, 5, 25, 18, 30)  # 18h30 — dentro do jantar (17–20h)
_AT_OUTSIDE = datetime(2026, 5, 25, 9, 0)   # 9h — fora de qualquer período


@pytest.fixture
def mock_schedule_repo():
    return AsyncMock(spec=RestaurantScheduleRepository)


@pytest.fixture
def mock_exception_repo():
    return AsyncMock(spec=RestaurantScheduleExceptionRepository)


@pytest.fixture
def service(mock_schedule_repo, mock_exception_repo):
    return MealPeriodService(
        schedule_repo=mock_schedule_repo,
        schedule_exception_repo=mock_exception_repo,
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _lunch_schedule(**kwargs):
    return RestaurantScheduleFactory.build(
        ru_id=_RU_ID,
        meal_period=MealPeriodEnum.LUNCH,
        opens_at=time(11, 0),
        closes_at=time(14, 0),
        weekday=_AT_LUNCH.weekday(),
        **kwargs,
    )


def _dinner_schedule(**kwargs):
    return RestaurantScheduleFactory.build(
        ru_id=_RU_ID,
        meal_period=MealPeriodEnum.DINNER,
        opens_at=time(17, 0),
        closes_at=time(20, 0),
        weekday=_AT_DINNER.weekday(),
        **kwargs,
    )


def _closed_all_day(**kwargs):
    return RestaurantScheduleExceptionFactory.build(
        ru_id=_RU_ID,
        exception_type=ExceptionTypeEnum.CLOSED,
        meal_period=None,
        **kwargs,
    )


def _closed_period(meal_period: MealPeriodEnum, **kwargs):
    return RestaurantScheduleExceptionFactory.build(
        ru_id=_RU_ID,
        exception_type=ExceptionTypeEnum.CLOSED,
        meal_period=meal_period,
        **kwargs,
    )


def _custom_hours(
    meal_period: MealPeriodEnum,
    opens_at: time,
    closes_at: time,
    **kwargs,
):
    return RestaurantScheduleExceptionFactory.build(
        ru_id=_RU_ID,
        exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
        meal_period=meal_period,
        opens_at=opens_at,
        closes_at=closes_at,
        **kwargs,
    )


# ── horários regulares ────────────────────────────────────────────────────────

class TestRegularSchedules:
    @pytest.mark.asyncio
    async def test_should_resolve_lunch_via_regular_schedule(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_resolve_dinner_via_regular_schedule(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_dinner_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER)

        assert result == MealPeriodEnum.DINNER

    @pytest.mark.asyncio
    async def test_should_resolve_correct_period_when_multiple_schedules_exist(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [
            _lunch_schedule(),
            _dinner_schedule(),
        ]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER)

        assert result == MealPeriodEnum.DINNER

    @pytest.mark.asyncio
    async def test_should_include_time_exactly_on_opens_at(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        at_opens = datetime(2026, 5, 25, 11, 0)  # exatamente em opens_at
        result = await service.resolve(ru_id=_RU_ID, at=at_opens)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_exclude_time_exactly_on_closes_at(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        at_closes = datetime(2026, 5, 25, 14, 0)  # exatamente em closes_at

        with pytest.raises(OutsideMealHoursError):
            await service.resolve(ru_id=_RU_ID, at=at_closes)

    @pytest.mark.asyncio
    async def test_should_not_call_schedule_repo_when_exception_causes_early_exit(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = [_closed_all_day()]

        with pytest.raises(RestaurantClosedAllDayError):
            await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        mock_schedule_repo.list_by_ru_id_and_weekday.assert_not_called()


# ── custom hours ──────────────────────────────────────────────────────────────

class TestCustomHours:
    @pytest.mark.asyncio
    async def test_should_resolve_lunch_via_custom_hours(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_resolve_dinner_via_custom_hours(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.DINNER, time(17, 0), time(21, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER)

        assert result == MealPeriodEnum.DINNER

    @pytest.mark.asyncio
    async def test_should_not_call_schedule_repo_when_custom_hours_match(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]

        await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        mock_schedule_repo.list_by_ru_id_and_weekday.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_fall_through_to_regular_schedule_when_custom_hours_do_not_match(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        # custom hours cobre 17–21h, mas horário testado é 12h
        custom = _custom_hours(MealPeriodEnum.DINNER, time(17, 0), time(21, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH
        mock_schedule_repo.list_by_ru_id_and_weekday.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_skip_custom_hours_with_none_opens_at(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, opens_at=None, closes_at=time(14, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH
        mock_schedule_repo.list_by_ru_id_and_weekday.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_skip_custom_hours_with_none_closes_at(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, opens_at=time(10, 0), closes_at=None)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH
        mock_schedule_repo.list_by_ru_id_and_weekday.assert_called_once()

    @pytest.mark.asyncio
    async def test_should_use_first_matching_custom_hours_when_multiple_exist(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom_lunch = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        custom_dinner = _custom_hours(MealPeriodEnum.DINNER, time(17, 0), time(21, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [
            custom_lunch,
            custom_dinner,
        ]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_ignore_closed_exceptions_when_looking_for_custom_hours(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        # CLOSED com meal_period != None não deve interferir na busca de CUSTOM_HOURS
        closed_dinner = _closed_period(MealPeriodEnum.DINNER)
        custom_lunch = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [
            closed_dinner,
            custom_lunch,
        ]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_include_time_exactly_on_custom_hours_opens_at(
        self, service, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(12, 0), time(14, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]

        at_opens = datetime(2026, 5, 25, 12, 0)  # exatamente em opens_at
        result = await service.resolve(ru_id=_RU_ID, at=at_opens)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_exclude_time_exactly_on_custom_hours_closes_at(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(12, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = []

        at_closes = datetime(2026, 5, 25, 12, 0)  # exatamente em closes_at

        with pytest.raises(OutsideMealHoursError):
            await service.resolve(ru_id=_RU_ID, at=at_closes)


# ── restaurante fechado o dia todo ────────────────────────────────────────────

class TestRestaurantClosedAllDay:
    @pytest.mark.asyncio
    async def test_should_raise_when_whole_day_closed_exception_exists(
        self, service, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = [_closed_all_day()]

        with pytest.raises(RestaurantClosedAllDayError):
            await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

    @pytest.mark.asyncio
    async def test_should_raise_even_when_regular_schedule_would_match(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = [_closed_all_day()]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        with pytest.raises(RestaurantClosedAllDayError):
            await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

    @pytest.mark.asyncio
    async def test_should_raise_even_when_custom_hours_also_exist(
        self, service, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [
            _closed_all_day(),
            custom,
        ]

        with pytest.raises(RestaurantClosedAllDayError):
            await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

    @pytest.mark.asyncio
    async def test_should_not_raise_when_closed_exception_has_specific_meal_period(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        # CLOSED com meal_period != None não é fechamento do dia todo
        closed_lunch = _closed_period(MealPeriodEnum.LUNCH)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [closed_lunch]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_dinner_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER)

        assert result == MealPeriodEnum.DINNER


# ── fora do horário de funcionamento ─────────────────────────────────────────

class TestOutsideMealHours:
    @pytest.mark.asyncio
    async def test_should_raise_when_no_exceptions_and_no_schedules(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = []

        with pytest.raises(OutsideMealHoursError):
            await service.resolve(ru_id=_RU_ID, at=_AT_OUTSIDE)

    @pytest.mark.asyncio
    async def test_should_raise_when_time_is_outside_regular_schedule(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        with pytest.raises(OutsideMealHoursError):
            await service.resolve(ru_id=_RU_ID, at=_AT_OUTSIDE)

    @pytest.mark.asyncio
    async def test_should_raise_when_custom_hours_do_not_match_and_no_regular_schedules(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.DINNER, time(17, 0), time(21, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = []

        with pytest.raises(OutsideMealHoursError):
            await service.resolve(ru_id=_RU_ID, at=_AT_OUTSIDE)

    @pytest.mark.asyncio
    async def test_should_raise_when_custom_hours_and_regular_schedule_do_not_match(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.DINNER, time(17, 0), time(21, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        with pytest.raises(OutsideMealHoursError):
            await service.resolve(ru_id=_RU_ID, at=_AT_OUTSIDE)


# ── período de refeição fechado ───────────────────────────────────────────────

class TestMealPeriodClosed:
    @pytest.mark.asyncio
    async def test_should_raise_when_resolved_period_has_closed_exception(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        closed = _closed_period(MealPeriodEnum.LUNCH)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [closed]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        with pytest.raises(MealPeriodClosedError):
            await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

    @pytest.mark.asyncio
    async def test_should_raise_for_dinner_when_dinner_period_is_closed(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        closed = _closed_period(MealPeriodEnum.DINNER)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [closed]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_dinner_schedule()]

        with pytest.raises(MealPeriodClosedError):
            await service.resolve(ru_id=_RU_ID, at=_AT_DINNER)

    @pytest.mark.asyncio
    async def test_should_not_raise_when_closed_exception_is_for_different_period(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        # DINNER está fechado, mas o horário resolve LUNCH
        closed_dinner = _closed_period(MealPeriodEnum.DINNER)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [closed_dinner]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_raise_when_custom_hours_resolve_period_that_is_closed(
        self, service, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        closed = _closed_period(MealPeriodEnum.LUNCH)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom, closed]

        with pytest.raises(MealPeriodClosedError):
            await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

    @pytest.mark.asyncio
    async def test_should_check_closed_period_after_resolving_not_before(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        # LUNCH fechado, mas o horário está dentro do DINNER — não deve levantar erro
        closed_lunch = _closed_period(MealPeriodEnum.LUNCH)
        mock_exception_repo.list_by_ru_id_and_date.return_value = [closed_lunch]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_dinner_schedule()]

        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER)

        assert result == MealPeriodEnum.DINNER


# ── chamadas ao repositório ───────────────────────────────────────────────────

class TestRepositoryCalls:
    @pytest.mark.asyncio
    async def test_should_call_exception_repo_with_correct_ru_id_and_date(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        mock_exception_repo.list_by_ru_id_and_date.assert_called_once_with(
            ru_id=_RU_ID,
            exception_date=_AT_LUNCH.date(),
        )

    @pytest.mark.asyncio
    async def test_should_call_schedule_repo_with_correct_ru_id_and_weekday(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        mock_exception_repo.list_by_ru_id_and_date.return_value = []
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        mock_schedule_repo.list_by_ru_id_and_weekday.assert_called_once_with(
            ru_id=_RU_ID,
            weekday=_AT_LUNCH.weekday(),
            only_active=True,
        )

    @pytest.mark.asyncio
    async def test_should_not_call_schedule_repo_when_custom_hours_resolve_period(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.LUNCH, time(10, 0), time(13, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]

        await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        mock_schedule_repo.list_by_ru_id_and_weekday.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_call_schedule_repo_when_custom_hours_do_not_match(
        self, service, mock_schedule_repo, mock_exception_repo
    ):
        custom = _custom_hours(MealPeriodEnum.DINNER, time(17, 0), time(21, 0))
        mock_exception_repo.list_by_ru_id_and_date.return_value = [custom]
        mock_schedule_repo.list_by_ru_id_and_weekday.return_value = [_lunch_schedule()]

        await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH)

        mock_schedule_repo.list_by_ru_id_and_weekday.assert_called_once()
