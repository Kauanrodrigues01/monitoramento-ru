from app.dependencies.headers import get_device_id_header


class TestGetDeviceIdHeader:
    def test_returns_device_id_when_header_is_present(self):
        result = get_device_id_header(x_device_id="abc-123")
        assert result == "abc-123"

    def test_returns_none_when_header_is_absent(self):
        result = get_device_id_header(x_device_id=None)
        assert result is None

    def test_returns_value_verbatim(self):
        result = get_device_id_header(x_device_id="uuid-v4-device-id")
        assert result == "uuid-v4-device-id"

    def test_returns_empty_string_when_header_is_empty(self):
        result = get_device_id_header(x_device_id="")
        assert result == ""
