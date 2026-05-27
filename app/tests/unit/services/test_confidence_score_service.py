from decimal import Decimal
from unittest.mock import patch


from app.services.confidence_score_service import (
    MIN_CONFIDENCE_SCORE,
    PENALTIES,
    ConfidenceScoreService,
)

# Coordenadas sem arredondamento suspeito (sem trailing zeros suficientes)
_NORMAL_LAT = Decimal("-3.747361")  # :.6f → "-3.747361" → termina em "1"
_NORMAL_LNG = Decimal("-38.523456")  # :.6f → "-38.523456" → termina em "56"

# Coordenadas com arredondamento suspeito (3+ zeros finais no formato :.6f)
_SUSPICIOUS_LAT = Decimal("-4.123000")  # :.6f → "-4.123000" → termina em "000"
_SUSPICIOUS_LNG = Decimal("-38.523456")  # normal; o lat já basta para disparar


# ===== SEM PENALIDADES =====


class TestCalculateConfidenceScoreNoPenalties:
    def test_returns_full_score_for_perfect_report(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("1.00")

    def test_accuracy_below_20_applies_no_penalty(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("1"),
        )

        assert result == Decimal("1.00")

    def test_accuracy_just_below_20_applies_no_penalty(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("19.99"),
        )

        assert result == Decimal("1.00")

    def test_accuracy_above_50_applies_no_penalty(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("51"),
        )

        assert result == Decimal("1.00")

    def test_accuracy_just_above_50_applies_no_penalty(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("50.01"),
        )

        assert result == Decimal("1.00")

    def test_returns_decimal_type(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert isinstance(result, Decimal)


# ===== PENALIDADE: LOCALIZAÇÃO SIMULADA (−0.80) =====


class TestCalculateConfidenceScoreMockLocation:
    def test_applies_mock_location_penalty(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=True,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("1.00") - PENALTIES["is_mock_location"]
        assert result == Decimal("0.20")

    def test_no_mock_location_penalty_when_false(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("1.00")

    def test_logs_warning_on_mock_location(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=True,
                accuracy_m=Decimal("10"),
            )

            mock_logger.warning.assert_called_once()

    def test_does_not_log_warning_when_not_mock(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("10"),
            )

            mock_logger.warning.assert_not_called()


# ===== PENALIDADE: ACCURACY AUSENTE OU ZERO (−0.30) =====


class TestCalculateConfidenceScoreAccuracyNoneOrZero:
    def test_applies_penalty_when_accuracy_m_is_none(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=None,
        )

        assert result == Decimal("1.00") - PENALTIES["accuracy_m_none_or_zero"]
        assert result == Decimal("0.70")

    def test_applies_penalty_when_accuracy_m_is_zero(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("0"),
        )

        assert result == Decimal("1.00") - PENALTIES["accuracy_m_none_or_zero"]
        assert result == Decimal("0.70")

    def test_none_and_zero_produce_same_score(self):
        result_none = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=None,
        )
        result_zero = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("0"),
        )

        assert result_none == result_zero

    def test_logs_debug_when_accuracy_m_is_none(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=None,
            )

            mock_logger.debug.assert_called()

    def test_logs_debug_when_accuracy_m_is_zero(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("0"),
            )

            mock_logger.debug.assert_called()


# ===== PENALIDADE: ACCURACY 20–50m (−0.15) =====


class TestCalculateConfidenceScoreAccuracy20To50:
    def test_applies_penalty_at_lower_boundary_20(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("20"),
        )

        assert result == Decimal("1.00") - PENALTIES["accuracy_m_20_to_50"]
        assert result == Decimal("0.85")

    def test_applies_penalty_at_upper_boundary_50(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("50"),
        )

        assert result == Decimal("0.85")

    def test_applies_penalty_in_middle_of_range(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("35"),
        )

        assert result == Decimal("0.85")

    def test_no_penalty_just_below_20(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("19.99"),
        )

        assert result == Decimal("1.00")

    def test_no_penalty_just_above_50(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("50.01"),
        )

        assert result == Decimal("1.00")

    def test_accuracy_none_zero_and_20_to_50_are_mutually_exclusive(self):
        # A condição usa elif — zero aciona accuracy_m_none_or_zero, não accuracy_m_20_to_50
        result_zero = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("0"),
        )
        result_small = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        # accuracy=0 aplica penalidade maior (0.30), accuracy=10 não aplica nenhuma
        assert result_zero < result_small

    def test_logs_debug_when_accuracy_m_in_range(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("35"),
            )

            mock_logger.debug.assert_called()

    def test_no_debug_logged_when_accuracy_has_no_penalty(self):
        # accuracy=10 não entra em nenhum branch de penalidade → nenhum debug emitido
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("10"),
            )

            mock_logger.debug.assert_not_called()


# ===== PENALIDADE: COORDENADAS SUSPEITAS (−0.25) =====


class TestCalculateConfidenceScoreSuspiciousCoordinates:
    def test_applies_penalty_for_suspicious_lat(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("1.00") - PENALTIES["suspicious_round_coordinates"]
        assert result == Decimal("0.75")

    def test_applies_penalty_for_suspicious_lng(self):
        # lng com trailing zeros suficientes para disparar a detecção
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=Decimal("-38.450000"),  # :.6f → "-38.450000" → termina em "0000"
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("0.75")

    def test_no_penalty_for_normal_coordinates(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("1.00")

    def test_applies_single_penalty_when_both_lat_and_lng_are_suspicious(self):
        # has_suspicious_round_coordinates usa `or` — ambas suspeitas não dobram a penalidade
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=Decimal("-4.123000"),  # suspeito
            lng=Decimal("-38.450000"),  # também suspeito
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result == Decimal("1.00") - PENALTIES["suspicious_round_coordinates"]
        assert result == Decimal("0.75")

    def test_logs_debug_on_suspicious_coordinates(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_SUSPICIOUS_LAT,
                lng=_SUSPICIOUS_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("10"),
            )

            mock_logger.debug.assert_called()

    def test_no_debug_logged_for_normal_coordinates(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("10"),
            )

            mock_logger.debug.assert_not_called()


# ===== PENALIDADES COMBINADAS =====


class TestCalculateConfidenceScoreCombined:
    def test_mock_plus_accuracy_none(self):
        # 1.00 - 0.80 - 0.30 = -0.10 → clamped to 0.05
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=True,
            accuracy_m=None,
        )

        assert result == MIN_CONFIDENCE_SCORE

    def test_mock_plus_accuracy_20_to_50(self):
        # 1.00 - 0.80 - 0.15 = 0.05 → exatamente no mínimo
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=True,
            accuracy_m=Decimal("35"),
        )

        assert result == MIN_CONFIDENCE_SCORE
        assert result == Decimal("0.05")

    def test_mock_plus_suspicious_coordinates(self):
        # 1.00 - 0.80 - 0.25 = -0.05 → clamped to 0.05
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=True,
            accuracy_m=Decimal("10"),
        )

        assert result == MIN_CONFIDENCE_SCORE

    def test_accuracy_none_plus_suspicious_coordinates(self):
        # 1.00 - 0.30 - 0.25 = 0.45
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=False,
            accuracy_m=None,
        )

        assert result == Decimal("0.45")

    def test_accuracy_20_to_50_plus_suspicious_coordinates(self):
        # 1.00 - 0.15 - 0.25 = 0.60
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("35"),
        )

        assert result == Decimal("0.60")

    def test_all_penalties_applied(self):
        # 1.00 - 0.80 - 0.30 - 0.25 = -0.35 → clamped to 0.05
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=True,
            accuracy_m=None,
        )

        assert result == MIN_CONFIDENCE_SCORE

    def test_mock_plus_accuracy_zero_plus_suspicious(self):
        # Mesmo que all_penalties mas com accuracy_m=0 em vez de None
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=True,
            accuracy_m=Decimal("0"),
        )

        assert result == MIN_CONFIDENCE_SCORE

    def test_mock_plus_accuracy_20_to_50_plus_suspicious(self):
        # 1.00 - 0.80 - 0.15 - 0.25 = -0.20 → clamped to 0.05
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=True,
            accuracy_m=Decimal("35"),
        )

        assert result == MIN_CONFIDENCE_SCORE


# ===== SEM LOGGING QUANDO NÃO HÁ PENALIDADES =====


class TestNoLoggingWhenNoPenalties:
    def test_no_warning_and_no_debug_when_no_penalties_apply(self):
        with patch("app.services.confidence_score_service.logger") as mock_logger:
            ConfidenceScoreService.calculate_confidence_score(
                lat=_NORMAL_LAT,
                lng=_NORMAL_LNG,
                is_mock_location=False,
                accuracy_m=Decimal("10"),
            )

            mock_logger.warning.assert_not_called()
            mock_logger.debug.assert_not_called()


# ===== SCORE MÍNIMO =====


class TestCalculateConfidenceScoreMinimum:
    def test_never_returns_below_minimum(self):
        # Todas as penalidades: 1.00 - 0.80 - 0.30 - 0.25 = -0.35
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_SUSPICIOUS_LAT,
            lng=_SUSPICIOUS_LNG,
            is_mock_location=True,
            accuracy_m=None,
        )

        assert result >= MIN_CONFIDENCE_SCORE

    def test_minimum_is_0_05(self):
        assert MIN_CONFIDENCE_SCORE == Decimal("0.05")

    def test_score_at_exact_minimum_boundary(self):
        # mock (−0.80) + accuracy 20–50 (−0.15) = −0.95 → 1.00 − 0.95 = 0.05 (exato)
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=True,
            accuracy_m=Decimal("35"),
        )

        assert result == Decimal("0.05")
        assert result == MIN_CONFIDENCE_SCORE

    def test_perfect_report_never_hits_minimum(self):
        result = ConfidenceScoreService.calculate_confidence_score(
            lat=_NORMAL_LAT,
            lng=_NORMAL_LNG,
            is_mock_location=False,
            accuracy_m=Decimal("10"),
        )

        assert result > MIN_CONFIDENCE_SCORE


# ===== CONSTANTES / PENALIDADES =====


class TestPenaltiesConstants:
    def test_mock_location_penalty_value(self):
        assert PENALTIES["is_mock_location"] == Decimal("0.80")

    def test_accuracy_none_or_zero_penalty_value(self):
        assert PENALTIES["accuracy_m_none_or_zero"] == Decimal("0.30")

    def test_accuracy_20_to_50_penalty_value(self):
        assert PENALTIES["accuracy_m_20_to_50"] == Decimal("0.15")

    def test_suspicious_round_coordinates_penalty_value(self):
        assert PENALTIES["suspicious_round_coordinates"] == Decimal("0.25")

    def test_minimum_confidence_score_value(self):
        assert MIN_CONFIDENCE_SCORE == Decimal("0.05")

    def test_ip_with_inconsistent_history_penalty_value(self):
        assert PENALTIES["ip_with_inconsistent_history"] == Decimal("0.25")

    def test_inconsistent_with_recent_history_penalty_value(self):
        assert PENALTIES["inconsistent_with_recent_history"] == Decimal("0.20")
