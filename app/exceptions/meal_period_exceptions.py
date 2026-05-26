from .base import AppException


class RestaurantClosedAllDayError(AppException):
    status_code = 400
    detail = "O restaurante está fechado hoje."


class MealPeriodClosedError(AppException):
    status_code = 400
    detail = "O restaurante está fechado neste período de refeição."


class OutsideMealHoursError(AppException):
    status_code = 400
    detail = "Fora do horário de funcionamento do restaurante."
