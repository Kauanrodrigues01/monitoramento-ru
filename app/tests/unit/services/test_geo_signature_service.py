import hashlib
import hmac
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.exceptions.geo_signature_exceptions import (
    ExpiredGeoSignatureException,
    InvalidGeoSignatureException,
)
from app.services.geo_signature_service import GeoSignatureService

_TEST_SECRET = "test-secret-key"
_TEST_LAT = Decimal("-3.747361")
_TEST_LNG = Decimal("-38.523060")
_TEST_ACCURACY = Decimal("12.5")
_NOW = 1748166600  # timestamp fixo para isolar os testes de time.time()
_MAX_SKEW = 60


def _sign(payload: str, secret: str = _TEST_SECRET) -> str:
    return hmac.new(
        key=secret.encode(),
        msg=payload.encode(),
        digestmod=hashlib.sha256,
    ).hexdigest()


def _patch_settings(secret=_TEST_SECRET, max_skew=_MAX_SKEW, debug=False):
    """Contexto que substitui settings por valores controlados."""
    mock = patch("app.services.geo_signature_service.settings")
    return mock


# ===== BUILD PAYLOAD =====


class TestBuildPayload:
    def test_formats_lat_with_6_decimal_places(self):
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )

        lat_part = payload.split("|")[0]
        assert lat_part == "-3.747361"

    def test_formats_lng_with_6_decimal_places(self):
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )

        lng_part = payload.split("|")[1]
        assert lng_part == "-38.523060"

    def test_formats_accuracy_m_with_1_decimal_place(self):
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, Decimal("12.5"), _NOW
        )

        accuracy_part = payload.split("|")[2]
        assert accuracy_part == "12.5"

    def test_accuracy_m_none_uses_null_literal(self):
        payload = GeoSignatureService.build_payload(_TEST_LAT, _TEST_LNG, None, _NOW)

        accuracy_part = payload.split("|")[2]
        assert accuracy_part == GeoSignatureService.NULL_ACCURACY_VALUE
        assert accuracy_part == "null"

    def test_accuracy_m_zero_formats_as_0_0_not_null(self):
        # Decimal("0") !== None — deve produzir "0.0", não "null"
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, Decimal("0"), _NOW
        )

        accuracy_part = payload.split("|")[2]
        assert accuracy_part == "0.0"
        assert accuracy_part != "null"

    def test_uses_pipe_as_separator(self):
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )

        assert payload.count("|") == 3

    def test_format_order_is_lat_lng_accuracy_timestamp(self):
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )
        parts = payload.split("|")

        assert len(parts) == 4
        assert parts[0] == "-3.747361"  # lat
        assert parts[1] == "-38.523060"  # lng
        assert parts[2] == "12.5"  # accuracy
        assert parts[3] == str(_NOW)  # timestamp

    def test_known_payload_with_accuracy(self):
        payload = GeoSignatureService.build_payload(
            Decimal("-4.225123"), Decimal("-38.730456"), Decimal("5.3"), 1716620000
        )

        assert payload == "-4.225123|-38.730456|5.3|1716620000"

    def test_known_payload_with_null_accuracy(self):
        payload = GeoSignatureService.build_payload(
            Decimal("-3.747361"), Decimal("-38.523060"), None, 1748166600
        )

        assert payload == "-3.747361|-38.523060|null|1748166600"

    def test_accuracy_m_is_rounded_to_1_decimal(self):
        # Decimal("5.37") → :.1f → "5.4"
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, Decimal("5.37"), _NOW
        )

        accuracy_part = payload.split("|")[2]
        assert accuracy_part == "5.4"

    def test_positive_coordinates_formatted_correctly(self):
        payload = GeoSignatureService.build_payload(
            Decimal("3.747361"), Decimal("38.523060"), None, _NOW
        )

        assert payload.startswith("3.747361|38.523060|")

    def test_timestamp_included_as_integer_string(self):
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )

        timestamp_part = payload.split("|")[3]
        assert timestamp_part == str(_NOW)
        assert "." not in timestamp_part

    def test_integer_accuracy_formats_with_decimal_point(self):
        # Decimal("12") com :.1f → "12.0", nunca "12"
        # O app mobile formata da mesma forma — qualquer divergência invalida a assinatura
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, Decimal("12"), _NOW
        )

        accuracy_part = payload.split("|")[2]
        assert accuracy_part == "12.0"
        assert "." in accuracy_part

    def test_null_accuracy_constant_value(self):
        # Alterar NULL_ACCURACY_VALUE quebraria silenciosamente a compatibilidade com o app mobile
        assert GeoSignatureService.NULL_ACCURACY_VALUE == "null"


# ===== GENERATE SIGNATURE =====


class TestGenerateSignature:
    def test_returns_64_char_string(self):
        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = _TEST_SECRET

            result = GeoSignatureService.generate_signature("payload")

            assert len(result) == 64

    def test_returns_lowercase_hex(self):
        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = _TEST_SECRET

            result = GeoSignatureService.generate_signature("payload")

            assert result == result.lower()
            assert all(c in "0123456789abcdef" for c in result)

    def test_is_deterministic(self):
        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = _TEST_SECRET

            r1 = GeoSignatureService.generate_signature("payload")
            r2 = GeoSignatureService.generate_signature("payload")

            assert r1 == r2

    def test_different_payloads_produce_different_signatures(self):
        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = _TEST_SECRET

            r1 = GeoSignatureService.generate_signature("payload-a")
            r2 = GeoSignatureService.generate_signature("payload-b")

            assert r1 != r2

    def test_matches_hmac_sha256_manual_computation(self):
        payload = "test-payload"
        expected = _sign(payload)

        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = _TEST_SECRET

            result = GeoSignatureService.generate_signature(payload)

            assert result == expected

    def test_different_secrets_produce_different_signatures(self):
        payload = "same-payload"

        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = "secret-a"
            sig_a = GeoSignatureService.generate_signature(payload)

        with patch("app.services.geo_signature_service.settings") as mock_settings:
            mock_settings.APP_GEO_SECRET = "secret-b"
            sig_b = GeoSignatureService.generate_signature(payload)

        assert sig_a != sig_b


# ===== VALIDATE TIMESTAMP =====


class TestValidateTimestamp:
    def _call(
        self,
        geo_timestamp: int,
        now: int = _NOW,
        max_skew: int = _MAX_SKEW,
        debug: bool = False,
    ):
        with (
            patch("time.time", return_value=now),
            patch("app.services.geo_signature_service.settings") as mock_settings,
        ):
            mock_settings.GEO_SIGNATURE_MAX_SKEW_SECONDS = max_skew
            mock_settings.DEBUG = debug
            GeoSignatureService._validate_timestamp(geo_timestamp)

    def test_accepts_current_timestamp(self):
        self._call(geo_timestamp=_NOW)

    def test_accepts_timestamp_within_skew_in_past(self):
        self._call(geo_timestamp=_NOW - 30)

    def test_accepts_timestamp_within_skew_in_future(self):
        # abs() garante que timestamps futuros dentro da janela também são aceitos
        self._call(geo_timestamp=_NOW + 30)

    def test_accepts_timestamp_at_exact_boundary(self):
        # time_difference == max_skew: condição é `> max_skew`, logo boundary é aceito
        self._call(geo_timestamp=_NOW - _MAX_SKEW)

    def test_accepts_future_timestamp_at_exact_boundary(self):
        self._call(geo_timestamp=_NOW + _MAX_SKEW)

    def test_rejects_timestamp_one_second_over_boundary(self):
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW - (_MAX_SKEW + 1))

    def test_rejects_timestamp_one_second_over_boundary_in_future(self):
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW + (_MAX_SKEW + 1))

    def test_rejects_timestamp_far_in_past(self):
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW - 3600)

    def test_rejects_timestamp_far_in_future(self):
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW + 3600)

    def test_debug_mode_accepts_timestamp_beyond_normal_skew(self):
        # Com DEBUG=True, janela é 86400s — deve aceitar o que normalmente seria rejeitado
        self._call(geo_timestamp=_NOW - (_MAX_SKEW + 100), debug=True)

    def test_debug_mode_accepts_timestamp_at_24h_boundary(self):
        self._call(geo_timestamp=_NOW - 86400, debug=True)

    def test_debug_mode_rejects_timestamp_beyond_24h(self):
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW - 86401, debug=True)

    def test_debug_mode_rejects_future_timestamp_beyond_24h(self):
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW + 86401, debug=True)

    def test_non_debug_uses_configured_max_skew(self):
        # max_skew=10 em vez de 60 — diff=11 deve rejeitar
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(geo_timestamp=_NOW - 11, max_skew=10, debug=False)

    def test_logs_warning_on_expired_timestamp(self):
        with (
            patch("time.time", return_value=_NOW),
            patch("app.services.geo_signature_service.settings") as mock_settings,
            patch("app.services.geo_signature_service.logger") as mock_logger,
        ):
            mock_settings.GEO_SIGNATURE_MAX_SKEW_SECONDS = _MAX_SKEW
            mock_settings.DEBUG = False

            with pytest.raises(ExpiredGeoSignatureException):
                GeoSignatureService._validate_timestamp(_NOW - 9999)

            mock_logger.warning.assert_called_once()

    def test_does_not_log_on_valid_timestamp(self):
        with (
            patch("time.time", return_value=_NOW),
            patch("app.services.geo_signature_service.settings") as mock_settings,
            patch("app.services.geo_signature_service.logger") as mock_logger,
        ):
            mock_settings.GEO_SIGNATURE_MAX_SKEW_SECONDS = _MAX_SKEW
            mock_settings.DEBUG = False

            GeoSignatureService._validate_timestamp(_NOW)

            mock_logger.warning.assert_not_called()


# ===== VALIDATE (fluxo completo) =====


class TestValidate:
    def _valid_signature(self, accuracy_m=_TEST_ACCURACY) -> str:
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, accuracy_m, _NOW
        )
        return _sign(payload)

    def _call(
        self,
        received_signature: str,
        geo_timestamp: int = _NOW,
        accuracy_m: Decimal | None = _TEST_ACCURACY,
    ):
        with (
            patch("time.time", return_value=_NOW),
            patch("app.services.geo_signature_service.settings") as mock_settings,
        ):
            mock_settings.APP_GEO_SECRET = _TEST_SECRET
            mock_settings.GEO_SIGNATURE_MAX_SKEW_SECONDS = _MAX_SKEW
            mock_settings.DEBUG = False
            GeoSignatureService.validate(
                lat=_TEST_LAT,
                lng=_TEST_LNG,
                accuracy_m=accuracy_m,
                geo_timestamp=geo_timestamp,
                received_signature=received_signature,
            )

    def test_valid_signature_does_not_raise(self):
        self._call(received_signature=self._valid_signature())

    def test_invalid_signature_raises_exception(self):
        with pytest.raises(InvalidGeoSignatureException):
            self._call(received_signature="a" * 64)

    def test_expired_timestamp_raises_before_sig_check(self):
        # Mesmo que a assinatura seja correta, timestamp expirado deve ser rejeitado primeiro
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(
                received_signature=self._valid_signature(),
                geo_timestamp=_NOW - 9999,
            )

    def test_valid_with_null_accuracy_m(self):
        sig = self._valid_signature(accuracy_m=None)

        self._call(received_signature=sig, accuracy_m=None)

    def test_wrong_signature_raises_invalid_not_expired(self):
        with pytest.raises(InvalidGeoSignatureException):
            self._call(received_signature="b" * 64)

    def test_signature_mismatch_due_to_wrong_secret_raises(self):
        # Assina com secret errado → backend usa secret correto → mismatch
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )
        wrong_sig = _sign(payload, secret="wrong-secret")

        with pytest.raises(InvalidGeoSignatureException):
            self._call(received_signature=wrong_sig)

    def test_logs_warning_on_invalid_signature(self):
        with (
            patch("time.time", return_value=_NOW),
            patch("app.services.geo_signature_service.settings") as mock_settings,
            patch("app.services.geo_signature_service.logger") as mock_logger,
        ):
            mock_settings.APP_GEO_SECRET = _TEST_SECRET
            mock_settings.GEO_SIGNATURE_MAX_SKEW_SECONDS = _MAX_SKEW
            mock_settings.DEBUG = False

            with pytest.raises(InvalidGeoSignatureException):
                GeoSignatureService.validate(
                    lat=_TEST_LAT,
                    lng=_TEST_LNG,
                    accuracy_m=_TEST_ACCURACY,
                    geo_timestamp=_NOW,
                    received_signature="a" * 64,
                )

            mock_logger.warning.assert_called_once()

    def test_logs_debug_on_valid_signature(self):
        with (
            patch("time.time", return_value=_NOW),
            patch("app.services.geo_signature_service.settings") as mock_settings,
            patch("app.services.geo_signature_service.logger") as mock_logger,
        ):
            mock_settings.APP_GEO_SECRET = _TEST_SECRET
            mock_settings.GEO_SIGNATURE_MAX_SKEW_SECONDS = _MAX_SKEW
            mock_settings.DEBUG = False

            sig = self._valid_signature()
            GeoSignatureService.validate(
                lat=_TEST_LAT,
                lng=_TEST_LNG,
                accuracy_m=_TEST_ACCURACY,
                geo_timestamp=_NOW,
                received_signature=sig,
            )

            mock_logger.debug.assert_called()
            mock_logger.warning.assert_not_called()

    def test_expired_checked_before_signature_with_wrong_sig(self):
        # Com timestamp expirado E assinatura errada, a exceção deve ser ExpiredGeoSignatureException
        with pytest.raises(ExpiredGeoSignatureException):
            self._call(
                received_signature="a" * 64,
                geo_timestamp=_NOW - 9999,
            )

    def test_null_accuracy_produces_different_signature_than_zero(self):
        sig_null = self._valid_signature(accuracy_m=None)
        sig_zero = self._valid_signature(accuracy_m=Decimal("0"))

        assert sig_null != sig_zero

    def test_uppercase_signature_is_rejected(self):
        # O service não normaliza maiúsculas — hmac.compare_digest é case-sensitive
        payload = GeoSignatureService.build_payload(
            _TEST_LAT, _TEST_LNG, _TEST_ACCURACY, _NOW
        )
        correct_sig = _sign(payload)

        with pytest.raises(InvalidGeoSignatureException):
            self._call(received_signature=correct_sig.upper())

    def test_valid_with_accuracy_m_zero(self):
        sig = self._valid_signature(accuracy_m=Decimal("0"))

        self._call(received_signature=sig, accuracy_m=Decimal("0"))
