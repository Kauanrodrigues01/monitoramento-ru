from .base import AppException


class RequiredDeviceIdHeaderError(AppException):
    status_code = 400
    detail = "O header 'X-Device-ID' é obrigatório."
