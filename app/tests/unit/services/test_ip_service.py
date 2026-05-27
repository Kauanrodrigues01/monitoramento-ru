import hashlib
from unittest.mock import MagicMock

from fastapi import Request

from app.services.ip_service import IpService


def _make_request(
    headers: dict | None = None,
    client_host: str | None = None,
) -> Request:
    mock = MagicMock(spec=Request)
    headers_dict = headers or {}
    mock.headers.get = lambda key, default=None: headers_dict.get(key, default)

    if client_host is not None:
        mock.client = MagicMock()
        mock.client.host = client_host
    else:
        mock.client = None

    return mock


# ===== GET CLIENT IP =====


class TestGetClientIpCfConnectingIp:
    def test_returns_cf_connecting_ip_when_present(self):
        request = _make_request(headers={"CF-Connecting-IP": "1.2.3.4"})

        result = IpService.get_client_ip(request)

        assert result == "1.2.3.4"

    def test_strips_whitespace_from_cf_connecting_ip(self):
        request = _make_request(headers={"CF-Connecting-IP": "  1.2.3.4  "})

        result = IpService.get_client_ip(request)

        assert result == "1.2.3.4"

    def test_empty_cf_ip_falls_through_to_next_source(self):
        request = _make_request(
            headers={
                "CF-Connecting-IP": "",
                "X-Forwarded-For": "5.6.7.8",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == "5.6.7.8"


class TestGetClientIpXForwardedFor:
    def test_returns_first_ip_from_x_forwarded_for(self):
        request = _make_request(headers={"X-Forwarded-For": "10.0.0.1"})

        result = IpService.get_client_ip(request)

        assert result == "10.0.0.1"

    def test_returns_first_ip_when_multiple_proxies_present(self):
        request = _make_request(
            headers={"X-Forwarded-For": "10.0.0.1, 172.16.0.1, 192.168.0.1"}
        )

        result = IpService.get_client_ip(request)

        assert result == "10.0.0.1"

    def test_strips_whitespace_from_first_ip(self):
        request = _make_request(headers={"X-Forwarded-For": "  10.0.0.1 , 172.16.0.1"})

        result = IpService.get_client_ip(request)

        assert result == "10.0.0.1"

    def test_returns_ipv6_as_first_entry(self):
        # IPv6 no início da cadeia X-Forwarded-For deve ser extraído corretamente
        request = _make_request(
            headers={"X-Forwarded-For": "2001:db8::1, 172.16.0.1, 192.168.0.1"}
        )

        result = IpService.get_client_ip(request)

        assert result == "2001:db8::1"

    def test_empty_x_forwarded_for_falls_through_to_next_source(self):
        request = _make_request(
            headers={
                "X-Forwarded-For": "",
                "X-Real-IP": "9.9.9.9",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == "9.9.9.9"


class TestGetClientIpXRealIp:
    def test_returns_x_real_ip_when_present(self):
        request = _make_request(headers={"X-Real-IP": "203.0.113.5"})

        result = IpService.get_client_ip(request)

        assert result == "203.0.113.5"

    def test_strips_whitespace_from_x_real_ip(self):
        request = _make_request(headers={"X-Real-IP": "  203.0.113.5  "})

        result = IpService.get_client_ip(request)

        assert result == "203.0.113.5"

    def test_empty_x_real_ip_falls_through_to_client_host(self):
        request = _make_request(
            headers={"X-Real-IP": ""},
            client_host="127.0.0.1",
        )

        result = IpService.get_client_ip(request)

        assert result == "127.0.0.1"


class TestGetClientIpDirectConnection:
    def test_returns_client_host_when_no_proxy_headers(self):
        request = _make_request(client_host="127.0.0.1")

        result = IpService.get_client_ip(request)

        assert result == "127.0.0.1"

    def test_returns_unknown_when_no_headers_and_no_client(self):
        request = _make_request()

        result = IpService.get_client_ip(request)

        assert result == "unknown"

    def test_returns_unknown_when_client_is_none(self):
        request = _make_request(headers={}, client_host=None)

        result = IpService.get_client_ip(request)

        assert result == "unknown"


class TestGetClientIpPriority:
    def test_cf_ip_takes_priority_over_x_forwarded_for(self):
        request = _make_request(
            headers={
                "CF-Connecting-IP": "1.1.1.1",
                "X-Forwarded-For": "2.2.2.2",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == "1.1.1.1"

    def test_cf_ip_takes_priority_over_x_real_ip(self):
        request = _make_request(
            headers={
                "CF-Connecting-IP": "1.1.1.1",
                "X-Real-IP": "3.3.3.3",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == "1.1.1.1"

    def test_cf_ip_takes_priority_over_client_host(self):
        request = _make_request(
            headers={"CF-Connecting-IP": "1.1.1.1"},
            client_host="127.0.0.1",
        )

        result = IpService.get_client_ip(request)

        assert result == "1.1.1.1"

    def test_x_forwarded_for_takes_priority_over_x_real_ip(self):
        request = _make_request(
            headers={
                "X-Forwarded-For": "2.2.2.2",
                "X-Real-IP": "3.3.3.3",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == "2.2.2.2"

    def test_x_forwarded_for_takes_priority_over_client_host(self):
        request = _make_request(
            headers={"X-Forwarded-For": "2.2.2.2"},
            client_host="127.0.0.1",
        )

        result = IpService.get_client_ip(request)

        assert result == "2.2.2.2"

    def test_x_real_ip_takes_priority_over_client_host(self):
        request = _make_request(
            headers={"X-Real-IP": "3.3.3.3"},
            client_host="127.0.0.1",
        )

        result = IpService.get_client_ip(request)

        assert result == "3.3.3.3"

    def test_cf_ip_wins_when_all_sources_present(self):
        request = _make_request(
            headers={
                "CF-Connecting-IP": "1.1.1.1",
                "X-Forwarded-For": "2.2.2.2, proxy",
                "X-Real-IP": "3.3.3.3",
            },
            client_host="127.0.0.1",
        )

        result = IpService.get_client_ip(request)

        assert result == "1.1.1.1"

    def test_falls_back_through_full_chain_to_unknown(self):
        request = _make_request(
            headers={
                "CF-Connecting-IP": "",
                "X-Forwarded-For": "",
                "X-Real-IP": "",
            },
            client_host=None,
        )

        result = IpService.get_client_ip(request)

        assert result == "unknown"

    def test_whitespace_only_cf_ip_does_not_fall_through(self):
        # "   " é truthy → o if entra, mas strip() devolve "".
        # A função retorna "" em vez de tentar a próxima fonte.
        request = _make_request(
            headers={
                "CF-Connecting-IP": "   ",
                "X-Forwarded-For": "2.2.2.2",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == ""

    def test_whitespace_only_x_real_ip_does_not_fall_through(self):
        # Mesmo comportamento para X-Real-IP com apenas espaços
        request = _make_request(
            headers={"X-Real-IP": "   "},
            client_host="127.0.0.1",
        )

        result = IpService.get_client_ip(request)

        assert result == ""

    def test_whitespace_only_x_forwarded_for_does_not_fall_through(self):
        # "   ".split(",")[0].strip() = "" — truthy check entra, resultado é ""
        request = _make_request(
            headers={
                "X-Forwarded-For": "   ",
                "X-Real-IP": "9.9.9.9",
            }
        )

        result = IpService.get_client_ip(request)

        assert result == ""


# ===== HASH IP =====


class TestHashIp:
    def test_returns_64_char_string(self):
        result = IpService.hash_ip("192.168.0.1")

        assert len(result) == 64

    def test_returns_lowercase_hex(self):
        result = IpService.hash_ip("192.168.0.1")

        assert result == result.lower()
        assert all(c in "0123456789abcdef" for c in result)

    def test_is_deterministic(self):
        ip = "10.0.0.1"

        assert IpService.hash_ip(ip) == IpService.hash_ip(ip)

    def test_different_ips_produce_different_hashes(self):
        assert IpService.hash_ip("1.2.3.4") != IpService.hash_ip("1.2.3.5")

    def test_uses_sha256_algorithm(self):
        ip = "172.16.0.1"
        expected = hashlib.sha256(ip.encode()).hexdigest()

        result = IpService.hash_ip(ip)

        assert result == expected

    def test_hash_of_unknown_is_consistent(self):
        # "unknown" é o valor passado quando o IP não pode ser determinado —
        # o hash deve ser sempre o mesmo para não gerar falsos positivos de cooldown
        expected = hashlib.sha256(b"unknown").hexdigest()

        result = IpService.hash_ip("unknown")

        assert result == expected

    def test_hash_of_loopback(self):
        expected = hashlib.sha256(b"127.0.0.1").hexdigest()

        result = IpService.hash_ip("127.0.0.1")

        assert result == expected

    def test_ip_with_port_produces_different_hash_than_without(self):
        assert IpService.hash_ip("1.2.3.4") != IpService.hash_ip("1.2.3.4:8080")

    def test_ipv6_address(self):
        ipv6 = "2001:db8::1"
        expected = hashlib.sha256(ipv6.encode()).hexdigest()

        result = IpService.hash_ip(ipv6)

        assert result == expected
