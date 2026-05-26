from datetime import datetime, time
from unittest.mock import MagicMock

import pytest

from app.core.utils import infer_meal_period
from app.models.restaurant import MealPeriodEnum


def _make_schedule(opens_at: time, closes_at: time, meal_period: MealPeriodEnum):
    s = MagicMock()
    s.opens_at = opens_at
    s.closes_at = closes_at
    s.meal_period = meal_period
    return s


def _make_exception(
    opens_at: time | None,
    closes_at: time | None,
    meal_period: MealPeriodEnum,
):
    e = MagicMock()
    e.opens_at = opens_at
    e.closes_at = closes_at
    e.meal_period = meal_period
    return e


def _at(h: int, m: int = 0) -> datetime:
    return datetime(2024, 1, 15, h, m, 0)


# ===== SEM SCHEDULES NEM EXCEPTIONS =====

class TestInferMealPeriodEmpty:
    def test_returns_none_when_both_none(self):
        result = infer_meal_period(at=_at(12))

        assert result is None

    def test_returns_none_when_both_empty_lists(self):
        result = infer_meal_period(at=_at(12), schedules=[], schedules_exceptions=[])

        assert result is None

    def test_returns_none_with_empty_schedules_only(self):
        result = infer_meal_period(at=_at(12), schedules=[])

        assert result is None

    def test_returns_none_with_empty_exceptions_only(self):
        result = infer_meal_period(at=_at(12), schedules_exceptions=[])

        assert result is None


# ===== SCHEDULE EXCEPTIONS =====

class TestInferMealPeriodWithExceptions:
    def test_returns_period_when_time_inside_exception_window(self):
        exc = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(12, 30), schedules_exceptions=[exc])

        assert result == MealPeriodEnum.LUNCH

    def test_returns_none_when_time_outside_exception_window(self):
        exc = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(15), schedules_exceptions=[exc])

        assert result is None

    def test_match_at_exact_opens_at_boundary(self):
        # opens_at <= report_time: deve incluir o limite inferior
        exc = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(11, 0), schedules_exceptions=[exc])

        assert result == MealPeriodEnum.LUNCH

    def test_no_match_at_exact_closes_at_boundary(self):
        # report_time < closes_at: deve excluir o limite superior
        exc = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(14, 0), schedules_exceptions=[exc])

        assert result is None

    def test_skips_exception_with_none_opens_at(self):
        exc = _make_exception(None, time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(12), schedules_exceptions=[exc])

        assert result is None

    def test_skips_exception_with_none_closes_at(self):
        exc = _make_exception(time(11, 0), None, MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(12), schedules_exceptions=[exc])

        assert result is None

    def test_skips_exception_with_both_times_none(self):
        exc = _make_exception(None, None, MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(12), schedules_exceptions=[exc])

        assert result is None

    def test_returns_dinner_when_time_in_dinner_exception(self):
        exc_lunch = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)
        exc_dinner = _make_exception(time(17, 30), time(20, 0), MealPeriodEnum.DINNER)

        result = infer_meal_period(at=_at(18), schedules_exceptions=[exc_lunch, exc_dinner])

        assert result == MealPeriodEnum.DINNER

    def test_first_matching_exception_wins(self):
        exc1 = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)
        exc2 = _make_exception(time(10, 0), time(15, 0), MealPeriodEnum.DINNER)

        result = infer_meal_period(at=_at(12), schedules_exceptions=[exc1, exc2])

        assert result == MealPeriodEnum.LUNCH


# ===== SCHEDULES REGULARES =====

class TestInferMealPeriodWithSchedules:
    def test_returns_period_when_time_inside_schedule_window(self):
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(12), schedules=[schedule])

        assert result == MealPeriodEnum.LUNCH

    def test_returns_none_when_time_outside_schedule_window(self):
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(15), schedules=[schedule])

        assert result is None

    def test_match_at_exact_opens_at_boundary(self):
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(11, 0), schedules=[schedule])

        assert result == MealPeriodEnum.LUNCH

    def test_no_match_at_exact_closes_at_boundary(self):
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(at=_at(14, 0), schedules=[schedule])

        assert result is None

    def test_matches_dinner_schedule(self):
        lunch = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)
        dinner = _make_schedule(time(17, 30), time(20, 0), MealPeriodEnum.DINNER)

        result = infer_meal_period(at=_at(18), schedules=[lunch, dinner])

        assert result == MealPeriodEnum.DINNER

    def test_first_matching_schedule_wins(self):
        s1 = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)
        s2 = _make_schedule(time(10, 0), time(15, 0), MealPeriodEnum.DINNER)

        result = infer_meal_period(at=_at(12), schedules=[s1, s2])

        assert result == MealPeriodEnum.LUNCH


# ===== PRIORIDADE: EXCEPTIONS > SCHEDULES =====

class TestExceptionsPriorityOverSchedules:
    def test_exception_match_skips_schedule_lookup(self):
        exc = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.DINNER)
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(
            at=_at(12),
            schedules=[schedule],
            schedules_exceptions=[exc],
        )

        assert result == MealPeriodEnum.DINNER

    def test_falls_back_to_schedule_when_no_exception_matches(self):
        exc = _make_exception(time(17, 30), time(20, 0), MealPeriodEnum.DINNER)
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(
            at=_at(12),
            schedules=[schedule],
            schedules_exceptions=[exc],
        )

        assert result == MealPeriodEnum.LUNCH

    def test_returns_none_when_exception_skipped_and_schedule_misses(self):
        exc = _make_exception(None, None, MealPeriodEnum.LUNCH)
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(
            at=_at(15),
            schedules=[schedule],
            schedules_exceptions=[exc],
        )

        assert result is None

    def test_exception_with_none_times_falls_back_to_schedule(self):
        # Exception sem horário deve ser ignorada; schedule cobre o horário
        exc = _make_exception(None, None, MealPeriodEnum.DINNER)
        schedule = _make_schedule(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)

        result = infer_meal_period(
            at=_at(12),
            schedules=[schedule],
            schedules_exceptions=[exc],
        )

        assert result == MealPeriodEnum.LUNCH

    def test_time_between_periods_returns_none(self):
        exc_lunch = _make_exception(time(11, 0), time(14, 0), MealPeriodEnum.LUNCH)
        exc_dinner = _make_exception(time(17, 30), time(20, 0), MealPeriodEnum.DINNER)

        # 16h está entre o almoço e o jantar
        result = infer_meal_period(
            at=_at(16),
            schedules_exceptions=[exc_lunch, exc_dinner],
        )

        assert result is None
