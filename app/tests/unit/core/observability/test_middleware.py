from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import Request

from app.core.observability.middleware import (
    BUSINESS_TAGS,
    business_metrics_middleware,
)

_PATCH_TRACK = "app.core.observability.middleware.track_business_request"


def _make_request(method: str = "GET") -> Request:
    mock_request = MagicMock(spec=Request)
    mock_request.method = method
    mock_request.scope = {}
    return mock_request


def _make_route(path: str, tags: list) -> MagicMock:
    route = MagicMock()
    route.path = path
    route.tags = tags
    return route


def _make_call_next(status_code: int = 200) -> AsyncMock:
    response = MagicMock()
    response.status_code = status_code
    return AsyncMock(return_value=response)


# ── TestBusinessTags ──────────────────────────────────────────────────────────


class TestBusinessTags:
    def test_business_tags_is_not_empty(self):
        assert len(BUSINESS_TAGS) > 0

    def test_business_tags_is_a_set(self):
        assert isinstance(BUSINESS_TAGS, set)


# ── TestBusinessMetricsMiddleware ─────────────────────────────────────────────


class TestBusinessMetricsMiddleware:
    async def test_returns_response_when_no_route_in_scope(self):
        request = _make_request()
        request.scope = {}
        call_next = _make_call_next(200)

        with patch(_PATCH_TRACK) as mock_track:
            response = await business_metrics_middleware(request, call_next)

        assert response.status_code == 200
        mock_track.assert_not_called()

    async def test_returns_response_when_route_has_no_business_tags(self):
        request = _make_request()
        request.scope = {"route": _make_route("/health", tags=["health"])}
        call_next = _make_call_next(200)

        with patch(_PATCH_TRACK) as mock_track:
            response = await business_metrics_middleware(request, call_next)

        assert response.status_code == 200
        mock_track.assert_not_called()

    async def test_tracks_request_when_route_has_business_tag(self):
        business_tag = next(iter(BUSINESS_TAGS))
        request = _make_request(method="GET")
        request.scope = {
            "route": _make_route("/api/v1/restaurants", tags=[business_tag])
        }
        call_next = _make_call_next(200)

        with patch(_PATCH_TRACK) as mock_track:
            await business_metrics_middleware(request, call_next)

        mock_track.assert_called_once_with(
            endpoint="/api/v1/restaurants",
            method="GET",
            status_code=200,
        )

    async def test_tracks_correct_status_code(self):
        business_tag = next(iter(BUSINESS_TAGS))
        request = _make_request(method="POST")
        request.scope = {
            "route": _make_route("/api/v1/queue-reports", tags=[business_tag])
        }
        call_next = _make_call_next(201)

        with patch(_PATCH_TRACK) as mock_track:
            await business_metrics_middleware(request, call_next)

        mock_track.assert_called_once_with(
            endpoint="/api/v1/queue-reports",
            method="POST",
            status_code=201,
        )

    async def test_tracks_correct_http_method(self):
        business_tag = next(iter(BUSINESS_TAGS))
        request = _make_request(method="DELETE")
        request.scope = {
            "route": _make_route("/api/v1/restaurants/{id}", tags=[business_tag])
        }
        call_next = _make_call_next(204)

        with patch(_PATCH_TRACK) as mock_track:
            await business_metrics_middleware(request, call_next)

        call_kwargs = mock_track.call_args.kwargs
        assert call_kwargs["method"] == "DELETE"

    async def test_does_not_track_when_route_tags_empty(self):
        request = _make_request()
        request.scope = {"route": _make_route("/api/v1/internal", tags=[])}
        call_next = _make_call_next(200)

        with patch(_PATCH_TRACK) as mock_track:
            await business_metrics_middleware(request, call_next)

        mock_track.assert_not_called()

    async def test_does_not_track_when_route_has_no_tags_attribute(self):
        route = MagicMock(spec=[])  # spec vazio: nenhum atributo disponível
        route.path = "/internal"
        request = _make_request()
        request.scope = {"route": route}
        call_next = _make_call_next(200)

        with patch(_PATCH_TRACK) as mock_track:
            await business_metrics_middleware(request, call_next)

        mock_track.assert_not_called()

    async def test_always_calls_call_next(self):
        request = _make_request()
        request.scope = {}
        call_next = _make_call_next(200)

        await business_metrics_middleware(request, call_next)

        call_next.assert_called_once_with(request)

    async def test_returns_response_from_call_next_regardless_of_tracking(self):
        business_tag = next(iter(BUSINESS_TAGS))
        request = _make_request()
        request.scope = {
            "route": _make_route("/api/v1/restaurants", tags=[business_tag])
        }
        call_next = _make_call_next(500)

        with patch(_PATCH_TRACK):
            response = await business_metrics_middleware(request, call_next)

        assert response.status_code == 500
