from fastapi import Depends
from fastapi.security import APIKeyHeader

from app.core.settings import settings
from app.exceptions.auth import InvalidAdminApiKeyError

api_key_scheme = APIKeyHeader(
    name="X-Admin-Key",
    description=(
        "Chave de acesso administrativo. Obrigatória em alguns endpoints de criação e edição.\n\n"
        "Obtenha a chave com o administrador do sistema."
    ),
    auto_error=False,
)


async def require_admin_api_key(
    api_key: str | None = Depends(api_key_scheme),
) -> None:
    if api_key != settings.ADMIN_API_KEY:
        raise InvalidAdminApiKeyError()
