from decimal import Decimal

from app.core.geo_utils import GeoUtils
from app.core.logging import get_logger
from app.models.queue_reports import ReportStatusEnum
from app.models.queue_snapshot import QueueSnapshot
from app.services.snapshot_status_service import STATUS_MAP_VALUE

logger = get_logger(__name__)

PENALTIES = {
    "is_mock_location": Decimal("0.80"),
    "accuracy_m_none_or_zero": Decimal("0.30"),
    "accuracy_m_20_to_50": Decimal("0.15"),
    # lat/lng com precisão suspeita (coordenadas redondas)
    "suspicious_round_coordinates": Decimal("0.25"),
    # Relato diverge do consenso recente — penalidade varia com a distância
    "inconsistent_with_recent_history_severe": Decimal("0.25"),  # distance >= 2.0
    "inconsistent_with_recent_history_moderate": Decimal("0.15"),  # distance >= 1.5
}

MIN_CONFIDENCE_SCORE = Decimal("0.05")


class ConfidenceScoreService:
    @staticmethod
    def calculate_confidence_score(
        lat: Decimal,
        lng: Decimal,
        is_mock_location: bool,
        accuracy_m: Decimal | None,
        report_status: ReportStatusEnum | None = None,
        snapshot: QueueSnapshot | None = None,
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

        if (
            snapshot is not None
            and snapshot.avg_status_value is not None
            and report_status is not None
            and report_status in STATUS_MAP_VALUE
        ):
            status_value = STATUS_MAP_VALUE[report_status]
            distance = abs(snapshot.avg_status_value - Decimal(status_value))

            if distance >= Decimal("2.0"):
                confidence_score -= PENALTIES["inconsistent_with_recent_history_severe"]
                logger.debug(
                    "Penalidade severa: divergência com histórico recente (distance=%.2f)",
                    distance,
                )
            elif distance >= Decimal("1.5"):
                confidence_score -= PENALTIES[
                    "inconsistent_with_recent_history_moderate"
                ]
                logger.debug(
                    "Penalidade moderada: divergência com histórico recente (distance=%.2f)",
                    distance,
                )

        return max(confidence_score, MIN_CONFIDENCE_SCORE)
