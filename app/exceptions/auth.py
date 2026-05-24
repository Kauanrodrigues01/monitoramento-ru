from app.exceptions.base import AppException


class InvalidAdminApiKeyError(AppException):
    status_code = 401
    detail = "Credenciais inválidas."
