from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request

from app.core.exception_handlers import app_exception_handler
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

        import json

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
