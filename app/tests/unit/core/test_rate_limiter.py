from unittest.mock import MagicMock, patch

import pytest

from app.core.rate_limiter import rate_limit_key


def _make_request(device_id: str | None = None, client_ip: str | None = None) -> MagicMock:
    request = MagicMock()
    request.headers = {}
    if device_id is not None:
        request.headers["X-Device-ID"] = device_id
    request.client = MagicMock()
    request.client.host = client_ip or "127.0.0.1"
    return request


class TestRateLimitKey:
    def test_uses_device_id_when_present(self):
        request = _make_request(device_id="abc-device-123")

        result = rate_limit_key(request)

        assert result == "device:abc-device-123"

    def test_device_id_takes_priority_over_ip(self):
        request = _make_request(device_id="abc-device-123", client_ip="10.0.0.1")

        result = rate_limit_key(request)

        assert result == "device:abc-device-123"

    def test_falls_back_to_ip_when_device_id_absent(self):
        request = _make_request()

        with patch("app.core.rate_limiter.IpService.get_client_ip", return_value="192.168.1.1"):
            result = rate_limit_key(request)

        assert result == "ip:192.168.1.1"

    def test_falls_back_to_ip_when_device_id_is_empty_string(self):
        request = _make_request(device_id="")

        with patch("app.core.rate_limiter.IpService.get_client_ip", return_value="10.0.0.5"):
            result = rate_limit_key(request)

        assert result == "ip:10.0.0.5"

    def test_returns_anonymous_when_no_device_id_and_no_ip(self):
        request = _make_request()

        with patch("app.core.rate_limiter.IpService.get_client_ip", return_value=None):
            result = rate_limit_key(request)

        assert result == "anonymous"

    def test_ip_key_includes_resolved_ip(self):
        request = _make_request()
        resolved_ip = "203.0.113.42"

        with patch("app.core.rate_limiter.IpService.get_client_ip", return_value=resolved_ip):
            result = rate_limit_key(request)

        assert result == f"ip:{resolved_ip}"

    def test_device_key_includes_full_device_id(self):
        device_id = "550e8400-e29b-41d4-a716-446655440000"
        request = _make_request(device_id=device_id)

        result = rate_limit_key(request)

        assert result == f"device:{device_id}"
