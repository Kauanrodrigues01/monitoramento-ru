from datetime import datetime

import pytest

from app.models.restaurant import MealPeriodEnum
from app.services.debug_meal_period_service import DebugMealPeriodService

_RU_ID = 1

# ── referências de horário ────────────────────────────────────────────────────

_AT_LUNCH_MID = datetime(2026, 5, 26, 12, 0)  # 12:00 — meio do almoço
_AT_DINNER_MID = datetime(2026, 5, 26, 19, 0)  # 19:00 — meio do jantar
_AT_LUNCH_START = datetime(2026, 5, 26, 5, 0)  # 05:00 — início exato do almoço
_AT_LUNCH_END = datetime(2026, 5, 26, 16, 59)  # 16:59 — último minuto do almoço
_AT_DINNER_START = datetime(2026, 5, 26, 17, 0)  # 17:00 — início exato do jantar
_AT_DINNER_EARLY = datetime(2026, 5, 26, 4, 59)  # 04:59 — madrugada (jantar)
_AT_MIDNIGHT = datetime(2026, 5, 26, 0, 0)  # 00:00 — meia-noite (jantar)


@pytest.fixture
def service() -> DebugMealPeriodService:
    return DebugMealPeriodService()


# ── almoço ────────────────────────────────────────────────────────────────────


class TestLunchPeriod:
    @pytest.mark.asyncio
    async def test_should_return_lunch_during_midday(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH_MID)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_return_lunch_at_05h00_boundary(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH_START)

        assert result == MealPeriodEnum.LUNCH

    @pytest.mark.asyncio
    async def test_should_return_lunch_at_16h59_last_minute(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_LUNCH_END)

        assert result == MealPeriodEnum.LUNCH


# ── jantar ────────────────────────────────────────────────────────────────────


class TestDinnerPeriod:
    @pytest.mark.asyncio
    async def test_should_return_dinner_during_evening(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER_MID)

        assert result == MealPeriodEnum.DINNER

    @pytest.mark.asyncio
    async def test_should_return_dinner_at_17h00_boundary(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER_START)

        assert result == MealPeriodEnum.DINNER

    @pytest.mark.asyncio
    async def test_should_return_dinner_at_04h59_early_morning(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_DINNER_EARLY)

        assert result == MealPeriodEnum.DINNER

    @pytest.mark.asyncio
    async def test_should_return_dinner_at_midnight(self, service):
        result = await service.resolve(ru_id=_RU_ID, at=_AT_MIDNIGHT)

        assert result == MealPeriodEnum.DINNER


# ── comportamento independente de ru_id ──────────────────────────────────────


class TestRuIdIgnored:
    @pytest.mark.asyncio
    async def test_should_return_same_period_regardless_of_ru_id(self, service):
        result_1 = await service.resolve(ru_id=1, at=_AT_LUNCH_MID)
        result_2 = await service.resolve(ru_id=99, at=_AT_LUNCH_MID)

        assert result_1 == result_2 == MealPeriodEnum.LUNCH
