from schemas.errors import ErrorResponse


def error_response(exc: type) -> dict:
    return {
        exc.status_code: {
            "model": ErrorResponse,
            "description": exc.detail,
            "content": {"application/json": {"example": {"detail": exc.detail}}},
        }
    }
