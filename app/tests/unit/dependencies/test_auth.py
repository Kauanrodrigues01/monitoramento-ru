from unittest.mock import patch

import pytest

from app.dependencies.auth import require_admin_api_key
from app.exceptions.auth import InvalidAdminApiKeyError


class TestRequireAdminApiKey:
    @pytest.mark.asyncio
    async def test_should_pass_when_key_is_correct(self):
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.ADMIN_API_KEY = "chave-secreta"

            await require_admin_api_key(api_key="chave-secreta")

    @pytest.mark.asyncio
    async def test_should_raise_error_when_key_is_wrong(self):
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.ADMIN_API_KEY = "chave-secreta"

            with pytest.raises(InvalidAdminApiKeyError):
                await require_admin_api_key(api_key="chave-errada")

    @pytest.mark.asyncio
    async def test_should_raise_error_when_key_is_none(self):
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.ADMIN_API_KEY = "chave-secreta"

            with pytest.raises(InvalidAdminApiKeyError):
                await require_admin_api_key(api_key=None)

    @pytest.mark.asyncio
    async def test_should_raise_error_when_key_is_empty_string(self):
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.ADMIN_API_KEY = "chave-secreta"

            with pytest.raises(InvalidAdminApiKeyError):
                await require_admin_api_key(api_key="")

    @pytest.mark.asyncio
    async def test_should_raise_error_when_key_has_extra_whitespace(self):
        with patch("app.dependencies.auth.settings") as mock_settings:
            mock_settings.ADMIN_API_KEY = "chave-secreta"

            with pytest.raises(InvalidAdminApiKeyError):
                await require_admin_api_key(api_key=" chave-secreta ")
