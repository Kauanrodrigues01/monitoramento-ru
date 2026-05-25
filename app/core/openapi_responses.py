from app.schemas.errors import ErrorResponse

INTERNAL_SERVER_ERROR_RESPONSE: dict = {
    500: {
        "model": ErrorResponse,
        "description": "Erro interno do servidor.",
        "content": {"application/json": {"example": {"detail": "Erro interno do servidor."}}},
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
