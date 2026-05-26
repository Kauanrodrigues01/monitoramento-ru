from datetime import datetime
from uuid import UUID

from app.core.geo_utils import GeoUtils
from app.core.logging import get_logger
from app.core.settings import settings
from app.exceptions.queue_report_exceptions import (
    QueueReportLocationOutOfGeofenceError,
    QueueReportTooRecentError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_reports import QueueReport
from app.models.restaurant import Restaurant
from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.schemas.queue_report_schemas import QueueReportCreate
from app.services.confidence_score_service import ConfidenceScoreService
from app.services.geo_signature_service import GeoSignatureService
from app.services.ip_service import IpService
from app.services.meal_period_service import MealPeriodService

logger = get_logger(__name__)

# campos do schema que não existem no model (validação/inferência apenas)
_SCHEMA_ONLY_FIELDS = {"geo_signature", "geo_timestamp"}


class QueueReportService:
    def __init__(
        self,
        repo: QueueReportRepository,
        restaurant_repo: RestaurantRepository,
        meal_period_service: MealPeriodService,
    ):
        self.repo = repo
        self.restaurant_repo = restaurant_repo
        self.meal_period_service = meal_period_service

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
        """
        Cria um relato de fila para um restaurante.

        Validações executadas em ordem:

        1. RESTAURANTE EXISTE E ESTÁ ATIVO
           Busca o restaurante pelo public_id. Lança RestaurantNotFoundError (404)
           se não existir ou estiver inativo (is_active=False).

        2. ASSINATURA DE GEOLOCALIZAÇÃO (GeoSignatureService)
           Verifica que o relato veio de um cliente legítimo com acesso à secret.
           - Timestamp: rejeita requisições com geo_timestamp fora da janela de
             GEO_SIGNATURE_MAX_SKEW_SECONDS (padrão 60s; 24h quando DEBUG=True).
             Protege contra replay attacks. → ExpiredGeoSignatureException (400)
           - HMAC-SHA256: reconstrói o payload `{lat:.6f}|{lng:.6f}|{accuracy_m:.1f}|{geo_timestamp}`
             e compara com a assinatura recebida em tempo constante (compare_digest).
             → InvalidGeoSignatureException (400)

        3. COOLDOWN POR IP (apenas IPs identificáveis)
           Impede que o mesmo IP envie mais de 1 relato a cada
           QUEUE_REPORT_COOLDOWN_MINUTES (padrão 3 min), contando apenas relatos
           que chegaram até o commit. IPs não identificáveis ("unknown") pulam esta
           verificação para não bloquear usuários anônimos entre si.
           → QueueReportTooRecentError (429)

        4. HORÁRIO DE FUNCIONAMENTO (MealPeriodService)
           Determina o meal_period do relato seguindo a ordem de prioridade:

           4a. Exceção CLOSED sem meal_period (dia inteiro fechado):
               → RestaurantClosedAllDayError (400)

           4b. Exceções CUSTOM_HOURS (horários alternativos):
               Substitui o horário regular do restaurante naquele período.

           4c. Horários regulares (fallback):
               Consultado apenas se nenhuma CUSTOM_HOURS cobriu o horário do relato.

           4d. Nenhum período encontrado:
               → OutsideMealHoursError (400)

           4e. Exceção CLOSED para o período específico:
               → MealPeriodClosedError (400)

        5. GEOFENCE (GeoUtils)
           Calcula a distância haversine entre as coordenadas do relato e as do
           restaurante. Rejeita se distance_m > geofence_radius_m.
           → QueueReportLocationOutOfGeofenceError (400)

        Campos calculados pelo servidor (não aceitos do cliente):
        - meal_period: inferido pelo horário do relato (MealPeriodService)
        - ip_hash: SHA-256 do IP resolvido (nunca armazenamos o IP real)
        - confidence_score: penalidades aplicadas por mock location, GPS impreciso
          (accuracy ausente/0 ou entre 20–50m) e coordenadas com arredondamento suspeito
        """
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

        meal_period = await self.meal_period_service.resolve(
            ru_id=restaurant.id, at=dt
        )

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

    async def list_recent_queue_reports(
        self, restaurant_public_id: UUID
    ) -> list[QueueReport]:
        """
        Retorna os últimos 20 relatos do período de refeição vigente para um restaurante.

        - Filtra por ru_id, meal_period atual e data de hoje.
        - meal_period é resolvido via MealPeriodService com o horário atual.
          Propaga RestaurantClosedAllDayError, OutsideMealHoursError ou
          MealPeriodClosedError se o restaurante não estiver em horário de funcionamento.
        - Limita a 20 relatos ordenados por created_at desc.
        """
        restaurant = await self._get_restaurant_by_public_id_or_error(
            restaurant_public_id
        )

        now = datetime.now()
        meal_period = await self.meal_period_service.resolve(
            ru_id=restaurant.id, at=now
        )

        return await self.repo.list_recent_by_period(
            ru_id=restaurant.id,
            meal_period=meal_period,
            day=now.date(),
            limit=20,
            offset=0,
        )
