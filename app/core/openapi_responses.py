from app.core.exception_handlers import _RATE_LIMIT_DETAIL
from app.schemas.errors import ErrorResponse

INTERNAL_SERVER_ERROR_RESPONSE: dict = {
    500: {
        "model": ErrorResponse,
        "description": "Erro interno do servidor.",
        "content": {
            "application/json": {"example": {"detail": "Erro interno do servidor."}}
        },
    }
}

RATE_LIMIT_RESPONSE: dict = {
    429: {
        "model": ErrorResponse,
        "description": "Muitas requisições. Limite de 1 relato a cada 3 minutos por IP.",
        "content": {"application/json": {"example": {"detail": _RATE_LIMIT_DETAIL}}},
    }
}


def error_response(exc: type) -> dict:
    return {
        exc.status_code: {
            "model": ErrorResponse,
            "description": exc.detail,
            "content": {"application/json": {"example": {"detail": exc.detail}}},
        }
    }
