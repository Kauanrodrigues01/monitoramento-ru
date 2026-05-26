from .base import AppException


class QueueReportLocationOutOfGeofenceError(AppException):
    status_code = 400
    detail = "Relato enviado muito longe do restaurante: fora do raio do restaurante."


class QueueReportTooRecentError(AppException):
    status_code = 429
    detail = "Você já enviou um relato recentemente. Aguarde alguns minutos antes de enviar outro."
