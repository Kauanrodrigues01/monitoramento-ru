from app.exceptions.base import AppException


class RestaurantAlreadyExistsError(AppException):
    status_code = 409
    detail = "Já existe um restaurante com esse nome."


class RestaurantNotFoundError(AppException):
    status_code = 404
    detail = "Restaurante não encontrado."
