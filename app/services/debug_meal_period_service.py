from datetime import datetime

from app.core.logging import get_logger
from app.models.restaurant import MealPeriodEnum
from app.services.meal_period_service import MealPeriodService

logger = get_logger(__name__)


class DebugMealPeriodService(MealPeriodService):
    """Substitui MealPeriodService quando DEBUG=True, sem consultar banco ou schedules.

    LUNCH  → 05:00 – 16:59
    DINNER → 17:00 – 04:59
    """

    def __init__(self) -> None:
        pass

    async def resolve(self, ru_id: int, at: datetime) -> MealPeriodEnum:
        meal_period = MealPeriodEnum.LUNCH if 5 <= at.hour < 17 else MealPeriodEnum.DINNER
        logger.debug(
            "[DEBUG] ru_id=%s período resolvido por horário: %s (sem consulta ao banco)",
            ru_id,
            meal_period.value,
        )
        return meal_period
