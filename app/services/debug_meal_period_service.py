from datetime import datetime

from app.models.restaurant import MealPeriodEnum
from app.services.meal_period_service import MealPeriodService


class DebugMealPeriodService(MealPeriodService):
    """Substitui MealPeriodService quando DEBUG=True, sem consultar banco ou schedules.

    LUNCH  → 05:00 – 16:59
    DINNER → 17:00 – 04:59
    """

    def __init__(self) -> None:
        pass

    async def resolve(self, ru_id: int, at: datetime) -> MealPeriodEnum:
        if 5 <= at.hour < 17:
            return MealPeriodEnum.LUNCH
        return MealPeriodEnum.DINNER
