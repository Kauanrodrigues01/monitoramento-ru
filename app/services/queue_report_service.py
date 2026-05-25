from datetime import datetime
from uuid import UUID

from app.core.geo_utils import GeoUtils
from app.core.logging import get_logger
from app.core.settings import settings
from app.core.utils import infer_meal_period
from app.exceptions.queue_report_exceptions import (
    QueueReportLocationOutOfGeofenceError,
    QueueReportOutsideMealHoursError,
    QueueReportTooRecentError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_reports import QueueReport
from app.models.restaurant import ExceptionTypeEnum, Restaurant
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.repositories.restaurant_schedule_repository import RestaurantScheduleRepository
from app.schemas.queue_report_schemas import QueueReportCreate
from app.services.confidence_score_service import ConfidenceScoreService
from app.services.geo_signature_service import GeoSignatureService
from app.services.ip_service import IpService

logger = get_logger(__name__)

# campos do schema que não existem no model (validação/inferência apenas)
_SCHEMA_ONLY_FIELDS = {"geo_signature", "geo_timestamp"}


class QueueReportService:
    def __init__(
        self,
        repo: QueueReportRepository,
        restaurant_repo: RestaurantRepository,
        schedule_repo: RestaurantScheduleRepository,
        schedule_exception_repo: RestaurantScheduleExceptionRepository,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo
        self.schedule_repo = schedule_repo
        self.schedule_exception_repo = schedule_exception_repo

    async def _get_restaurant_by_public_id_or_error(
        self, public_id: UUID
    ) -> Restaurant:
        restaurant = await self.restaurant_repo.get_by_public_id(public_id)

        if not restaurant:
            raise RestaurantNotFoundError()

        return restaurant

    async def create_queue_report(
        self,
        restaurant_public_id: UUID,
        queue_report_data: QueueReportCreate,
        ip: str | None,
    ) -> QueueReport:
        data = queue_report_data
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        unknown_ip = ip is None or ip == "unknown"

        if unknown_ip:
            logger.warning("IP do cliente não pôde ser determinado — cooldown ignorado")

        ip_hash = IpService.hash_ip(ip if not unknown_ip else "unknown")

        # Valida a assinatura de geolocalização, garante que veio de um app legítimo.
        # Feito antes do cooldown para não vazar estado do cooldown a requisições ilegítimas.
        GeoSignatureService.validate(
            lat=data.lat,
            lng=data.lng,
            accuracy_m=data.accuracy_m,
            geo_timestamp=data.geo_timestamp,
            received_signature=data.geo_signature,
        )

        if not unknown_ip:
            recent_report = await self.repo.get_last_by_ip_hash_within_minutes(
                ip_hash=ip_hash,
                minutes=settings.QUEUE_REPORT_COOLDOWN_MINUTES,
            )
            if recent_report:
                raise QueueReportTooRecentError()

        dt = datetime.fromtimestamp(data.geo_timestamp)

        # Carrega todas as exceções do RU para a data do relato de uma vez.
        # Isso cobre feriados, fechamentos pontuais e horários customizados.
        schedule_exceptions = await self.schedule_exception_repo.list_by_ru_id_and_date(
            ru_id=restaurant.id,
            exception_date=dt.date(),
        )

        # PASSO 1 — Exceção de dia inteiro (meal_period IS NULL, exception_type=CLOSED).
        #
        # Verificamos isso primeiro porque não depende de saber qual período é o atual:
        # se o restaurante está fechado o dia todo, qualquer relato é inválido.
        #
        # Exceções CLOSED não têm opens_at/closes_at (são NULL por design do modelo),
        # então não é possível fazer match por janela de horário — a verificação precisa
        # ser feita pelo campo meal_period da própria exceção.
        whole_day_closed = next(
            (
                e
                for e in schedule_exceptions
                if e.exception_type == ExceptionTypeEnum.CLOSED
                and e.meal_period
                is None  # meal_period IS NULL indica fechamento dia inteiro
            ),
            None,
        )
        if whole_day_closed:
            raise QueueReportOutsideMealHoursError()

        # PASSO 2 — Exceções CUSTOM_HOURS têm opens_at/closes_at definidos e substituem
        # o horário regular do restaurante naquele período.
        #
        # Tentamos inferir o meal_period a partir dessas exceções antes de consultar
        # os horários regulares, pois elas têm prioridade sobre o schedule normal.
        #
        # Exceções CLOSED são ignoradas aqui porque não possuem janela de horário
        # e são, por constraint do banco, mutuamente exclusivas com CUSTOM_HOURS
        # para o mesmo (ru_id, data, meal_period).
        custom_hours_exceptions = [
            e
            for e in schedule_exceptions
            if e.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        ]
        meal_period = infer_meal_period(
            at=dt, schedules_exceptions=custom_hours_exceptions
        )

        # PASSO 3 — Fallback para os horários regulares do restaurante.
        #
        # Só consultamos o banco aqui se nenhuma CUSTOM_HOURS cobriu o horário do relato,
        # evitando uma query desnecessária quando há exceção de horário ativa.
        if meal_period is None:
            schedules = await self.schedule_repo.list_active_by_ru_id_and_weekday(
                ru_id=restaurant.id,
                weekday=dt.weekday(),
            )
            meal_period = infer_meal_period(at=dt, schedules=schedules)

        if meal_period is None:
            raise QueueReportOutsideMealHoursError()

        # PASSO 4 — Exceção CLOSED para período específico.
        #
        # Só podemos verificar isso após conhecer o meal_period (passos 2 ou 3),
        # porque CLOSED de período específico não tem janela de horário — a única
        # forma de saber se ele bloqueia o relato é comparar meal_period == meal_period
        # da exceção. Ex.: CLOSED/LUNCH bloqueia relato de almoço, mas não o de jantar.
        period_closed = next(
            (
                e
                for e in schedule_exceptions
                if e.exception_type == ExceptionTypeEnum.CLOSED
                and e.meal_period == meal_period
            ),
            None,
        )
        if period_closed:
            raise QueueReportOutsideMealHoursError()

        confidence_score = ConfidenceScoreService.calculate_confidence_score(
            lat=data.lat,
            lng=data.lng,
            is_mock_location=data.is_mock_location,
            accuracy_m=data.accuracy_m,
        )

        distance_m = GeoUtils.haversine_distance_m(
            lat1=float(data.lat),
            lng1=float(data.lng),
            lat2=float(restaurant.lat),
            lng2=float(restaurant.lng),
        )

        if distance_m > restaurant.geofence_radius_m:
            logger.warning(
                "Relato fora do geofence: ru_id=%s, distance_m=%.1f, geofence_radius_m=%d",
                restaurant.id,
                distance_m,
                restaurant.geofence_radius_m,
            )
            raise QueueReportLocationOutOfGeofenceError()

        try:
            queue_report = await self.repo.create(
                QueueReport(
                    ru_id=restaurant.id,
                    meal_period=meal_period,
                    ip_hash=ip_hash,
                    confidence_score=confidence_score,
                    geo_signature_valid=True,
                    **data.model_dump(exclude=_SCHEMA_ONLY_FIELDS),
                )
            )
            await self.repo.db_session.commit()
        except Exception:
            await self.repo.db_session.rollback()
            raise

        logger.info(
            "Queue report criado: public_id=%s, ru_id=%s, status=%s, distance_m=%.1f",
            queue_report.public_id,
            queue_report.ru_id,
            queue_report.status.value,
            distance_m,
        )

        return queue_report
