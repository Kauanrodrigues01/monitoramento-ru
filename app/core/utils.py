from datetime import datetime

from app.models.restaurant import (
    MealPeriodEnum,
    RestaurantSchedule,
    RestaurantScheduleException,
)


def infer_meal_period(
    at: datetime,
    schedules: list[RestaurantSchedule] | None = None,
    schedules_exceptions: list[RestaurantScheduleException] | None = None,
) -> MealPeriodEnum | None:
    report_time = at.time()

    if schedules_exceptions:
        for exception in schedules_exceptions:
            if exception.opens_at is None or exception.closes_at is None:
                continue
            if exception.opens_at <= report_time < exception.closes_at:
                return exception.meal_period

    if schedules:
        for schedule in schedules:
            if schedule.opens_at <= report_time < schedule.closes_at:
                return schedule.meal_period

    return None
