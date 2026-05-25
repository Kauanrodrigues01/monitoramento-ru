from app.exceptions.base import AppException


class RestaurantAlreadyExistsError(AppException):
    status_code = 409
    detail = "Já existe um restaurante com esse nome."


class RestaurantNotFoundError(AppException):
    status_code = 404
    detail = "Restaurante não encontrado."


class RestaurantScheduleAlreadyExistsError(AppException):
    status_code = 409
    detail = "Já existe um horário cadastrado para esse restaurante, dia da semana e período de refeição."


class RestaurantScheduleNotFoundError(AppException):
    status_code = 404
    detail = "Horário do restaurante não encontrado."


class RestaurantScheduleOpensBeforeClosesError(AppException):
    status_code = 400
    detail = "O horário de abertura deve ser anterior ao horário de fechamento."
