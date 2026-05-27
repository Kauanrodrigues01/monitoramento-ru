import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request
from slowapi.errors import RateLimitExceeded

from app.core.exception_handlers import (
    _RATE_LIMIT_DETAIL,
    app_exception_handler,
    rate_limit_exceeded_handler,
)
from app.exceptions.base import AppException


def _make_request(path: str = "/test") -> Request:
    mock = MagicMock(spec=Request)
    mock.url.path = path
    return mock


def _make_exception(status_code: int, detail: str = "mensagem de erro") -> AppException:
    exc = AppException(detail=detail)
    exc.status_code = status_code
    return exc


class TestAppExceptionHandler:
    @pytest.mark.asyncio
    async def test_should_return_json_response_with_correct_status_code(self):
        exc = _make_exception(status_code=404)

        response = await app_exception_handler(_make_request(), exc)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_should_return_json_response_with_correct_detail(self):
        exc = _make_exception(status_code=409, detail="Recurso já existe.")

        response = await app_exception_handler(_make_request(), exc)

        body = json.loads(response.body)
        assert body["detail"] == "Recurso já existe."

    @pytest.mark.asyncio
    async def test_should_log_warning_for_4xx_errors(self):
        exc = _make_exception(status_code=404, detail="Não encontrado.")
        request = _make_request(path="/restaurants/abc")

        with patch("app.core.exception_handlers.logger") as mock_logger:
            await app_exception_handler(request, exc)

            mock_logger.warning.assert_called_once()
            mock_logger.exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_log_exception_for_5xx_errors(self):
        exc = _make_exception(status_code=500, detail="Erro interno.")

        with patch("app.core.exception_handlers.logger") as mock_logger:
            await app_exception_handler(_make_request(), exc)

            mock_logger.exception.assert_called_once()
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_log_warning_for_boundary_4xx(self):
        exc = _make_exception(status_code=499)

        with patch("app.core.exception_handlers.logger") as mock_logger:
            await app_exception_handler(_make_request(), exc)

            mock_logger.warning.assert_called_once()
            mock_logger.exception.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_log_exception_for_boundary_5xx(self):
        exc = _make_exception(status_code=500)

        with patch("app.core.exception_handlers.logger") as mock_logger:
            await app_exception_handler(_make_request(), exc)

            mock_logger.exception.assert_called_once()
            mock_logger.warning.assert_not_called()

    @pytest.mark.asyncio
    async def test_should_include_request_path_in_warning_log(self):
        exc = _make_exception(status_code=404)
        request = _make_request(path="/restaurants/xyz")

        with patch("app.core.exception_handlers.logger") as mock_logger:
            await app_exception_handler(request, exc)

            log_args = mock_logger.warning.call_args[0]
            assert "/restaurants/xyz" in log_args


def _make_rate_limit_exc(headers: dict | None = None) -> MagicMock:
    exc = MagicMock(spec=RateLimitExceeded)
    exc.headers = headers
    return exc


class TestRateLimitExceededHandler:
    @pytest.mark.asyncio
    async def test_should_return_429_status_code(self):
        exc = _make_rate_limit_exc()

        response = await rate_limit_exceeded_handler(_make_request(), exc)

        assert response.status_code == 429

    @pytest.mark.asyncio
    async def test_should_return_correct_detail_message(self):
        exc = _make_rate_limit_exc()

        response = await rate_limit_exceeded_handler(_make_request(), exc)

        body = json.loads(response.body)
        assert body["detail"] == _RATE_LIMIT_DETAIL

    @pytest.mark.asyncio
    async def test_should_include_headers_from_exc_when_present(self):
        exc = _make_rate_limit_exc(headers={"Retry-After": "60"})

        response = await rate_limit_exceeded_handler(_make_request(), exc)

        assert response.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_should_not_add_extra_headers_when_exc_has_none(self):
        exc = _make_rate_limit_exc(headers=None)

        response = await rate_limit_exceeded_handler(_make_request(), exc)

        assert "Retry-After" not in response.headers
