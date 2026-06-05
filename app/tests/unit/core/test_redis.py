from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.core.redis as redis_module


@pytest.fixture(autouse=True)
def reset_redis_singleton():
    """Garante que o singleton é None antes de cada teste."""
    redis_module._redis_client = None
    yield
    redis_module._redis_client = None


class TestGetRedis:
    async def test_returns_redis_client(self):
        mock_client = MagicMock()
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client):
            result = await redis_module.get_redis()
        assert result is mock_client

    async def test_singleton_returns_same_instance_on_second_call(self):
        mock_client = MagicMock()
        with patch("app.core.redis.aioredis.from_url", return_value=mock_client) as mock_from_url:
            r1 = await redis_module.get_redis()
            r2 = await redis_module.get_redis()

        assert r1 is r2
        mock_from_url.assert_called_once()

    async def test_uses_settings_redis_url_when_configured(self):
        with (
            patch("app.core.redis.aioredis.from_url") as mock_from_url,
            patch("app.core.redis.settings") as mock_settings,
        ):
            mock_settings.REDIS_URL = "redis://custom-host:6380"
            await redis_module.get_redis()

        mock_from_url.assert_called_once_with(
            "redis://custom-host:6380",
            encoding="utf-8",
            decode_responses=True,
        )

    async def test_falls_back_to_default_url_when_redis_url_is_none(self):
        with (
            patch("app.core.redis.aioredis.from_url") as mock_from_url,
            patch("app.core.redis.settings") as mock_settings,
        ):
            mock_settings.REDIS_URL = None
            await redis_module.get_redis()

        mock_from_url.assert_called_once_with(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True,
        )


class TestCloseRedis:
    async def test_calls_aclose_on_client(self):
        mock_client = AsyncMock()
        redis_module._redis_client = mock_client

        await redis_module.close_redis()

        mock_client.aclose.assert_called_once()

    async def test_sets_client_to_none_after_close(self):
        redis_module._redis_client = AsyncMock()

        await redis_module.close_redis()

        assert redis_module._redis_client is None

    async def test_is_idempotent_when_no_client_exists(self):
        redis_module._redis_client = None

        await redis_module.close_redis()  # não deve levantar exceção

    async def test_subsequent_get_redis_creates_new_client_after_close(self):
        mock_client_1 = AsyncMock()
        mock_client_2 = MagicMock()
        redis_module._redis_client = mock_client_1

        await redis_module.close_redis()

        with patch("app.core.redis.aioredis.from_url", return_value=mock_client_2):
            result = await redis_module.get_redis()

        assert result is mock_client_2
