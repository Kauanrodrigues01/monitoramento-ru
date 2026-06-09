from unittest.mock import AsyncMock, patch

import pytest

from app.repositories.queue_report_repository import QueueReportRepository
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.repositories.restaurant_repository import RestaurantRepository
from app.services.meal_period_service import MealPeriodService
from app.services.queue_report_service import QueueReportService
from app.services.snapshot_status_service import SnapshotStatusService
from app.tests.factories.models.unit.restaurant_model_factory import RestaurantFactory
from app.tests.factories.schemas.queue_report_schema_factory import (
    build_queue_report_create_schema,
)
from app.tests.unit.services.queue_report_service._base import (
    _PATCH_OBSERVE_QUEUE_REPORT_CONFIDENCE_SCORE,
    _PATCH_OBSERVE_QUEUE_REPORT_DISTANCE,
    _PATCH_TRACK_QUEUE_REPORT_CREATED,
    _PATCH_TRACK_QUEUE_REPORT_REJECTED,
)

from ._base import (
    _GEO_TIMESTAMP,
)


@pytest.fixture
def restaurant():
    return RestaurantFactory.build(geofence_radius_m=100)


@pytest.fixture
def valid_payload():
    return build_queue_report_create_schema(geo_timestamp=_GEO_TIMESTAMP)


@pytest.fixture
def mock_repo():
    repo = AsyncMock(spec=QueueReportRepository)
    repo.db_session = AsyncMock()
    return repo


@pytest.fixture
def mock_restaurant_repo():
    return AsyncMock(spec=RestaurantRepository)


@pytest.fixture
def mock_snapshot_repo():
    return AsyncMock(spec=QueueSnapshotRepository)


@pytest.fixture
def mock_meal_period_service():
    return AsyncMock(spec=MealPeriodService)


@pytest.fixture
def mock_snapshot_status_service():
    return AsyncMock(spec=SnapshotStatusService)


@pytest.fixture(autouse=True)
def mock_observability():
    """
    Mocka automaticamente todas as métricas de observabilidade
    relacionadas ao QueueReportService.

    Objetivos:
    - Evitar que testes unitários alterem métricas reais do Prometheus.
    - Impedir efeitos colaterais causados pela camada de observabilidade.
    - Permitir validações específicas em testes que precisem verificar
      se uma métrica foi chamada corretamente.

    Como a fixture utiliza `autouse=True`, os patches são aplicados
    automaticamente em todos os testes deste módulo sem necessidade
    de declarar a fixture explicitamente.

    Em testes que precisarem validar chamadas das métricas, basta
    receber `mock_observability` como argumento e utilizar os mocks
    retornados.

    Exemplo:

        async def test_should_track_metric(
            mock_observability,
        ):
            ...

            mock_observability["created"].assert_called_once()
    """

    with (
        patch(_PATCH_TRACK_QUEUE_REPORT_CREATED) as created,
        patch(_PATCH_TRACK_QUEUE_REPORT_REJECTED) as rejected,
        patch(_PATCH_OBSERVE_QUEUE_REPORT_DISTANCE) as distance,
        patch(_PATCH_OBSERVE_QUEUE_REPORT_CONFIDENCE_SCORE) as confidence,
    ):
        yield {
            "created": created,
            "rejected": rejected,
            "distance": distance,
            "confidence": confidence,
        }


@pytest.fixture
def service(
    mock_repo,
    mock_restaurant_repo,
    mock_snapshot_repo,
    mock_meal_period_service,
    mock_snapshot_status_service,
):
    return QueueReportService(
        repo=mock_repo,
        restaurant_repo=mock_restaurant_repo,
        snapshot_repo=mock_snapshot_repo,
        meal_period_service=mock_meal_period_service,
        snapshot_status_service=mock_snapshot_status_service,
    )
