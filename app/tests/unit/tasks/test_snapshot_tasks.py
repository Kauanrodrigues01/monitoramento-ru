import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.snapshot_tasks import (
    _update_snapshot,
    update_restaurant_snapshot_status_task,
)

_PATCH_ASYNC_SESSION = "app.tasks.snapshot_tasks.AsyncSessionLocal"
_PATCH_GET_SERVICE = "app.tasks.snapshot_tasks.get_snapshot_status_service"
_PATCH_ASYNCIO_RUN = "app.tasks.snapshot_tasks.asyncio.run"


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_session_and_service():
    mock_service = MagicMock()
    mock_service.update_snapshot = AsyncMock()

    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)

    mock_session_factory = MagicMock(return_value=mock_session)

    return mock_session_factory, mock_session, mock_service


# ── TestUpdateRestaurantSnapshotStatusTask ────────────────────────────────────


class TestUpdateRestaurantSnapshotStatusTask:
    def test_calls_asyncio_run(self):
        # Garante que a task síncrona do Celery delega para asyncio.run
        with patch(_PATCH_ASYNCIO_RUN) as mock_run:
            update_restaurant_snapshot_status_task(ru_id=42)

        mock_run.assert_called_once()

    def test_asyncio_run_receives_coroutine_for_correct_ru_id(self):
        # Garante que a coroutine passada para asyncio.run é _update_snapshot(ru_id)
        captured = {}

        def _capture_coroutine(coro):
            captured["coro"] = coro
            coro.close()  # Evita ResourceWarning de coroutine nunca aguardada

        with patch(_PATCH_ASYNCIO_RUN, side_effect=_capture_coroutine):
            update_restaurant_snapshot_status_task(ru_id=7)

        assert asyncio.iscoroutine(captured["coro"])
        assert captured["coro"].cr_code.co_name == "_update_snapshot"

    def test_celery_task_name(self):
        assert (
            update_restaurant_snapshot_status_task.name
            == "snapshot_tasks.update_snapshot_status_task"
        )

    def test_celery_task_max_retries(self):
        assert update_restaurant_snapshot_status_task.max_retries == 3

    def test_celery_task_autoretry_for_exception(self):
        assert Exception in update_restaurant_snapshot_status_task.autoretry_for

    def test_celery_task_retry_backoff_enabled(self):
        assert update_restaurant_snapshot_status_task.retry_backoff is True


# ── TestUpdateSnapshot ────────────────────────────────────────────────────────


class TestUpdateSnapshot:
    async def test_calls_update_snapshot_with_correct_ru_id(self):
        mock_session_factory, mock_session, mock_service = _make_session_and_service()

        with (
            patch(_PATCH_ASYNC_SESSION, mock_session_factory),
            patch(_PATCH_GET_SERVICE, return_value=mock_service),
        ):
            await _update_snapshot(ru_id=42)

        mock_service.update_snapshot.assert_called_once_with(ru_id=42)

    async def test_opens_async_session(self):
        mock_session_factory, mock_session, mock_service = _make_session_and_service()

        with (
            patch(_PATCH_ASYNC_SESSION, mock_session_factory),
            patch(_PATCH_GET_SERVICE, return_value=mock_service),
        ):
            await _update_snapshot(ru_id=1)

        mock_session_factory.assert_called_once()
        mock_session.__aenter__.assert_called_once()
        mock_session.__aexit__.assert_called_once()

    async def test_passes_session_to_service_factory(self):
        mock_session_factory, mock_session, mock_service = _make_session_and_service()

        with (
            patch(_PATCH_ASYNC_SESSION, mock_session_factory),
            patch(_PATCH_GET_SERVICE, return_value=mock_service) as mock_get_service,
        ):
            await _update_snapshot(ru_id=99)

        mock_get_service.assert_called_once_with(db_session=mock_session)

    async def test_session_closed_even_when_update_raises(self):
        mock_session_factory, mock_session, mock_service = _make_session_and_service()
        mock_service.update_snapshot.side_effect = RuntimeError("db exploded")

        with (
            patch(_PATCH_ASYNC_SESSION, mock_session_factory),
            patch(_PATCH_GET_SERVICE, return_value=mock_service),
            pytest.raises(RuntimeError),
        ):
            await _update_snapshot(ru_id=5)

        # O context manager async deve chamar __aexit__ mesmo com exception
        mock_session.__aexit__.assert_called_once()

    async def test_propagates_exception_from_update_snapshot(self):
        mock_session_factory, mock_session, mock_service = _make_session_and_service()
        mock_service.update_snapshot.side_effect = ValueError("snapshot not found")

        with (
            patch(_PATCH_ASYNC_SESSION, mock_session_factory),
            patch(_PATCH_GET_SERVICE, return_value=mock_service),
            pytest.raises(ValueError, match="snapshot not found"),
        ):
            await _update_snapshot(ru_id=3)
