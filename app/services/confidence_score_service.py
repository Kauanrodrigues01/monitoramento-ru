from decimal import Decimal

from app.core.geo_utils import GeoUtils
from app.core.logging import get_logger

logger = get_logger(__name__)

PENALTIES = {
    "is_mock_location": Decimal("0.80"),
    "accuracy_m_none_or_zero": Decimal("0.30"),
    "accuracy_m_20_to_50": Decimal("0.15"),
    # lat/lng com precisão suspeita (coordenadas redondas)
    "suspicious_round_coordinates": Decimal("0.25"),
    # IP com histórico de relatos inconsistentes
    "ip_with_inconsistent_history": Decimal("0.25"),
    # Relato inconsistente com histórico recente do RU
    "inconsistent_with_recent_history": Decimal("0.20"),
}

MIN_CONFIDENCE_SCORE = Decimal("0.05")


class ConfidenceScoreService:
    @staticmethod
    def calculate_confidence_score(
        lat: Decimal,
        lng: Decimal,
        is_mock_location: bool,
        accuracy_m: Decimal | None,
    ) -> Decimal:
        confidence_score = Decimal("1.00")

        if is_mock_location:
            confidence_score -= PENALTIES["is_mock_location"]
            logger.warning("Penalidade aplicada: localização simulada detectada")

        if accuracy_m is None or accuracy_m == Decimal("0"):
            confidence_score -= PENALTIES["accuracy_m_none_or_zero"]
            logger.debug("Penalidade aplicada: accuracy_m ausente ou zero")
        elif Decimal("20") <= accuracy_m <= Decimal("50"):
            confidence_score -= PENALTIES["accuracy_m_20_to_50"]
            logger.debug(
                "Penalidade aplicada: accuracy_m entre 20m e 50m (accuracy_m=%.1f)",
                accuracy_m,
            )

        if GeoUtils.has_suspicious_round_coordinates(lat, lng):
            confidence_score -= PENALTIES["suspicious_round_coordinates"]
            logger.debug(
                "Penalidade aplicada: coordenadas suspeitas (lat=%s, lng=%s)", lat, lng
            )

        # Adicionar lógica para as penalidades: "ip_with_inconsistent_history" e "inconsistent_with_recent_history": ...

        return max(confidence_score, MIN_CONFIDENCE_SCORE)
