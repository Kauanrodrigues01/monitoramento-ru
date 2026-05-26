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
        "description": "Muitas requisições. Tente novamente em alguns instantes.",
        "content": {
            "application/json": {
                "example": {"detail": _RATE_LIMIT_DETAIL},
            }
        },
        "headers": {
            "Retry-After": {
                "description": "Tempo em segundos até uma nova tentativa ser permitida.",
                "schema": {"type": "integer"},
            },
            "X-RateLimit-Limit": {
                "description": "Limite máximo de requisições permitido.",
                "schema": {"type": "integer"},
            },
            "X-RateLimit-Remaining": {
                "description": "Quantidade restante de requisições disponíveis.",
                "schema": {"type": "integer"},
            },
        },
    }
}


def rate_limit_with_cooldown_response(cooldown_exc: type) -> dict:
    """429 com dois exemplos: cooldown de negócio específico + rate limit global do slowapi."""
    return {
        429: {
            "description": "Rate limit excedido ou cooldown ativo.",
            "content": {
                "application/json": {
                    "examples": {
                        "cooldown": {
                            "summary": "Cooldown por IP",
                            "value": {"detail": cooldown_exc.detail},
                        },
                        "rate_limit": {
                            "summary": "Rate limit global",
                            "value": {"detail": _RATE_LIMIT_DETAIL},
                        },
                    }
                }
            },
            "headers": RATE_LIMIT_RESPONSE[429]["headers"],
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
