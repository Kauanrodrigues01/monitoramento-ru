from .base import AppException


class InvalidGeoSignatureException(AppException):
    status_code = 400
    detail = "Assinatura de geolocalização é inválida."


class ExpiredGeoSignatureException(AppException):
    status_code = 400
    detail = "Assinatura de geolocalização expirou."
