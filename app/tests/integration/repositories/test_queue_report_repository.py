"""
Testes de integração para QueueReportRepository.

Estratégia de fixtures:
- `report_dataset` (scope="class") — persiste um conjunto fixo de reports
  uma única vez por classe de teste, equivalente ao setUpTestData do Django.
- `test_db_session` (scope padrão) — usado nos testes de escrita (create)
  e nos testes com tempo controlado via freezegun.

Sobre freezegun:
  Os métodos get_last_by_*_within_minutes, list_recent_by_period_within_minutes
  e count_within_minutes chamam utc_now() internamente. O patch é feito em
  app.core.datetime_utils.datetime (onde utc_now() chama datetime.now(UTC)),
  não no módulo do repositório.

  count_today() e list_recent_by_period() dependem do fuso America/Fortaleza
  (UTC-3), então os datetimes frozen precisam considerar essa conversão.
"""

from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from freezegun import freeze_time
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.queue_reports import QueueReport, ReportStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.repositories.queue_report_repository import QueueReportRepository
from app.tests.factories.models.integration.queue_report_model_factory import (
    QueueReportDBFactory,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantAurorasDBFactory,
    RestaurantPalmaresDBFactory,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ---------------------------------------------------------------------------
# Constantes de tempo usadas no dataset e nos testes
# ---------------------------------------------------------------------------

# "agora" fixo para o dataset — todos os reports são inseridos com created_at
# relativo a esse ponto, permitindo que os testes de janela temporal funcionem
# de forma determinística com freeze_time.
FROZEN_NOW = datetime(
    2025, 12, 25, 14, 0, 0, tzinfo=UTC
)  # 25/12 14:00 UTC = 11:00 Fortaleza

IP_HASH_A = "a" * 64
IP_HASH_B = "b" * 64
DEVICE_HASH_A = "c" * 64
DEVICE_HASH_B = "d" * 64


# ---------------------------------------------------------------------------
# Dataset compartilhado — criado uma vez por classe
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="class", loop_scope="session")
async def report_dataset(test_engine):
    """
    Persiste dois restaurantes e reports com created_at controlados manualmente,
    cobrindo os cenários de janela temporal e filtros por período/data.

    Restaurantes:
      - ru_palmares → RU principal dos testes
      - ru_auroras  → usado para validar isolamento por ru_id

    Mapa do dataset (todos os datetimes em UTC, FROZEN_NOW = 25/12 14:00 UTC):
    ┌─────────────────────────────┬──────────────────────────┬─────────────┬───────────┬──────────────┐
    │ chave                       │ created_at (UTC)         │ meal_period │  ip_hash  │ device_hash  │
    ├─────────────────────────────┼──────────────────────────┼─────────────┼───────────┼──────────────┤
    │ recent_lunch_ip_a           │ FROZEN_NOW - 5min        │    LUNCH    │  IP_A     │  DEVICE_A    │
    │ recent_lunch_ip_b           │ FROZEN_NOW - 10min       │    LUNCH    │  IP_B     │  DEVICE_B    │
    │ recent_dinner               │ FROZEN_NOW - 3min        │   DINNER    │  IP_A     │  DEVICE_A    │
    │ old_lunch                   │ FROZEN_NOW - 60min       │    LUNCH    │  IP_A     │  DEVICE_A    │
    │ yesterday_lunch             │ FROZEN_NOW - 26h         │    LUNCH    │  IP_A     │  DEVICE_A    │
    │ auroras_recent_lunch        │ FROZEN_NOW - 5min        │    LUNCH    │  IP_A     │  DEVICE_A    │
    └─────────────────────────────┴──────────────────────────┴─────────────┴───────────┴──────────────┘
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        async with session.begin():
            ru_palmares = RestaurantPalmaresDBFactory()
            ru_auroras = RestaurantAurorasDBFactory()
            session.add_all([ru_palmares, ru_auroras])
            await session.flush()
            await session.refresh(ru_palmares)
            await session.refresh(ru_auroras)

            # report recente de almoço — dentro de qualquer janela de 15min
            recent_lunch_ip_a = QueueReportDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.LUNCH,
                ip_hash=IP_HASH_A,
                device_hash=DEVICE_HASH_A,
                status=ReportStatusEnum.SMALL,
            )
            recent_lunch_ip_a.created_at = FROZEN_NOW - timedelta(minutes=5)

            # segundo report recente de almoço — IP e device diferentes
            recent_lunch_ip_b = QueueReportDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.LUNCH,
                ip_hash=IP_HASH_B,
                device_hash=DEVICE_HASH_B,
                status=ReportStatusEnum.MEDIUM,
            )
            recent_lunch_ip_b.created_at = FROZEN_NOW - timedelta(minutes=10)

            # report recente de jantar — mesmo IP/device do recent_lunch_ip_a
            recent_dinner = QueueReportDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.DINNER,
                ip_hash=IP_HASH_A,
                device_hash=DEVICE_HASH_A,
                status=ReportStatusEnum.LARGE,
            )
            recent_dinner.created_at = FROZEN_NOW - timedelta(minutes=3)

            # report antigo de almoço — fora de janelas de 15min mas no mesmo dia (UTC-3)
            old_lunch = QueueReportDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.LUNCH,
                ip_hash=IP_HASH_A,
                device_hash=DEVICE_HASH_A,
                status=ReportStatusEnum.NO_QUEUE,
            )
            old_lunch.created_at = FROZEN_NOW - timedelta(minutes=60)

            # report de ontem — fora do dia atual em Fortaleza (UTC-3)
            yesterday_lunch = QueueReportDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.LUNCH,
                ip_hash=IP_HASH_A,
                device_hash=DEVICE_HASH_A,
                status=ReportStatusEnum.SMALL,
            )
            yesterday_lunch.created_at = FROZEN_NOW - timedelta(hours=26)

            # report do ru_auroras — mesmo IP/device, mesmo horário
            auroras_recent_lunch = QueueReportDBFactory(
                ru_id=ru_auroras.id,
                meal_period=MealPeriodEnum.LUNCH,
                ip_hash=IP_HASH_A,
                device_hash=DEVICE_HASH_A,
                status=ReportStatusEnum.SMALL,
            )
            auroras_recent_lunch.created_at = FROZEN_NOW - timedelta(minutes=5)

            session.add_all(
                [
                    recent_lunch_ip_a,
                    recent_lunch_ip_b,
                    recent_dinner,
                    old_lunch,
                    yesterday_lunch,
                    auroras_recent_lunch,
                ]
            )
            await session.flush()

            for obj in [
                recent_lunch_ip_a,
                recent_lunch_ip_b,
                recent_dinner,
                old_lunch,
                yesterday_lunch,
                auroras_recent_lunch,
            ]:
                await session.refresh(obj)

        yield {
            "ru_palmares": ru_palmares,
            "ru_auroras": ru_auroras,
            "recent_lunch_ip_a": recent_lunch_ip_a,  # -5min,  LUNCH,  IP_A, DEVICE_A
            "recent_lunch_ip_b": recent_lunch_ip_b,  # -10min, LUNCH,  IP_B, DEVICE_B
            "recent_dinner": recent_dinner,  # -3min,  DINNER, IP_A, DEVICE_A
            "old_lunch": old_lunch,  # -60min, LUNCH,  IP_A, DEVICE_A
            "yesterday_lunch": yesterday_lunch,  # -26h,   LUNCH,  IP_A, DEVICE_A
            "auroras_recent_lunch": auroras_recent_lunch,  # -5min,  LUNCH,  IP_A, DEVICE_A (outro RU)
        }

        async with session.begin():
            for obj in [
                recent_lunch_ip_a,
                recent_lunch_ip_b,
                recent_dinner,
                old_lunch,
                yesterday_lunch,
                auroras_recent_lunch,
                ru_palmares,
                ru_auroras,
            ]:
                await session.delete(obj)


# ---------------------------------------------------------------------------
# Fixture de repositório
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def repo(test_db_session):
    return QueueReportRepository(test_db_session)


# ===========================================================================
# create
# ===========================================================================


class TestCreate:
    """
    Testes de escrita — isolados via rollback automático do test_db_session.
    Usa PALMARES porque create() não faz query de leitura — sem risco de
    interferir com o dataset (que também usa PALMARES) já que o rollback
    descarta tudo ao fim de cada teste.
    """

    @pytest_asyncio.fixture(scope="class", loop_scope="session")
    async def restaurant_for_create(self, test_engine):
        session_factory = async_sessionmaker(
            bind=test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_factory() as session:
            async with session.begin():
                restaurant = RestaurantPalmaresDBFactory()
                session.add(restaurant)
                await session.flush()
                await session.refresh(restaurant)

            yield restaurant

            async with session.begin():
                await session.delete(restaurant)

    async def test_persists_report_and_returns_it(self, repo, restaurant_for_create):
        report = QueueReportDBFactory(ru_id=restaurant_for_create.id)

        result = await repo.create(report)

        assert result is report

    async def test_assigns_id_after_create(self, repo, restaurant_for_create):
        report = QueueReportDBFactory(ru_id=restaurant_for_create.id)

        await repo.create(report)

        assert report.id is not None
        assert isinstance(report.id, int)

    async def test_assigns_public_id_after_create(self, repo, restaurant_for_create):
        from uuid import UUID

        report = QueueReportDBFactory(ru_id=restaurant_for_create.id)

        await repo.create(report)

        assert report.public_id is not None
        assert isinstance(report.public_id, UUID)

    async def test_assigns_created_at_after_create(self, repo, restaurant_for_create):
        report = QueueReportDBFactory(ru_id=restaurant_for_create.id)

        await repo.create(report)

        assert report.created_at is not None

    async def test_created_report_is_retrievable(self, repo, restaurant_for_create):
        report = QueueReportDBFactory(ru_id=restaurant_for_create.id)

        created = await repo.create(report)

        # confirma que o flush tornou o registro visível dentro da transação
        from sqlalchemy import select

        result = await repo.db_session.scalar(
            select(QueueReport).where(QueueReport.id == created.id)
        )
        assert result is not None

    async def test_create_does_not_commit(self, repo, restaurant_for_create):
        """
        create() só faz flush, não commit. O registro é visível na mesma
        transação mas o rollback do test_db_session o desfaz ao fim do teste.
        """
        report = QueueReportDBFactory(ru_id=restaurant_for_create.id)

        created = await repo.create(report)

        from sqlalchemy import select

        found = await repo.db_session.scalar(
            select(QueueReport).where(QueueReport.id == created.id)
        )
        assert found is not None  # visível via flush na transação aberta


# ===========================================================================
# get_last_by_ip_hash_within_minutes
# ===========================================================================


class TestGetLastByIpHashWithinMinutes:
    @freeze_time(FROZEN_NOW)
    async def test_returns_most_recent_report_for_ip(self, repo, report_dataset):
        """
        IP_A tem recent_lunch_ip_a (-5min) e recent_dinner (-3min) dentro de 15min.
        O mais recente é recent_dinner — deve ser retornado.
        """
        result = await repo.get_last_by_ip_hash_within_minutes(IP_HASH_A, minutes=15)

        assert result is not None
        assert result.id == report_dataset["recent_dinner"].id

    @freeze_time(FROZEN_NOW)
    async def test_returns_none_when_ip_has_no_recent_report(
        self, repo, report_dataset
    ):
        """old_lunch (-60min) está fora da janela de 15min."""
        # IP_A tem old_lunch em -60min; dentro de 15min tem recent_* também,
        # mas com janela de 1min nenhum report de IP_A estaria dentro
        result = await repo.get_last_by_ip_hash_within_minutes(IP_HASH_A, minutes=1)

        assert result is None

    @freeze_time(FROZEN_NOW)
    async def test_returns_none_for_unknown_ip_hash(self, repo):
        result = await repo.get_last_by_ip_hash_within_minutes("e" * 64, minutes=15)

        assert result is None

    @freeze_time(FROZEN_NOW)
    async def test_returns_report_for_ip_b_independently(self, repo, report_dataset):
        """IP_B só tem recent_lunch_ip_b (-10min) — deve retorná-lo."""
        result = await repo.get_last_by_ip_hash_within_minutes(IP_HASH_B, minutes=15)

        assert result is not None
        assert result.id == report_dataset["recent_lunch_ip_b"].id

    @freeze_time(FROZEN_NOW)
    async def test_excludes_report_outside_window(self, repo, report_dataset):
        """old_lunch (-60min) está fora de janela de 30min."""
        # IP_A tem reports em -3min, -5min e -60min
        # buscando com janela de 4min: apenas recent_dinner (-3min) entra
        result = await repo.get_last_by_ip_hash_within_minutes(IP_HASH_A, minutes=4)

        assert result is not None
        assert result.id == report_dataset["recent_dinner"].id


# ===========================================================================
# get_last_by_device_hash_within_minutes
# ===========================================================================


class TestGetLastByDeviceHashWithinMinutes:
    @freeze_time(FROZEN_NOW)
    async def test_returns_most_recent_report_for_device(self, repo, report_dataset):
        """
        DEVICE_A tem recent_lunch_ip_a (-5min), recent_dinner (-3min) e old_lunch (-60min).
        O mais recente dentro de 15min é recent_dinner.
        """
        result = await repo.get_last_by_device_hash_within_minutes(
            DEVICE_HASH_A, minutes=15
        )

        assert result is not None
        assert result.id == report_dataset["recent_dinner"].id

    @freeze_time(FROZEN_NOW)
    async def test_returns_none_when_device_has_no_recent_report(
        self, repo, report_dataset
    ):
        """Com janela de 1min, nenhum report de DEVICE_A está dentro."""
        result = await repo.get_last_by_device_hash_within_minutes(
            DEVICE_HASH_A, minutes=1
        )

        assert result is None

    @freeze_time(FROZEN_NOW)
    async def test_returns_none_for_unknown_device_hash(self, repo):
        result = await repo.get_last_by_device_hash_within_minutes("f" * 64, minutes=15)

        assert result is None

    @freeze_time(FROZEN_NOW)
    async def test_returns_report_for_device_b_independently(
        self, repo, report_dataset
    ):
        """DEVICE_B só tem recent_lunch_ip_b (-10min)."""
        result = await repo.get_last_by_device_hash_within_minutes(
            DEVICE_HASH_B, minutes=15
        )

        assert result is not None
        assert result.id == report_dataset["recent_lunch_ip_b"].id

    @freeze_time(FROZEN_NOW)
    async def test_excludes_old_report_outside_window(self, repo, report_dataset):
        """old_lunch (-60min) não entra em janela de 30min."""
        # com janela de 30min: recent_lunch_ip_a (-5min) e recent_dinner (-3min) entram
        # old_lunch (-60min) fica fora
        result = await repo.get_last_by_device_hash_within_minutes(
            DEVICE_HASH_A, minutes=30
        )

        assert result is not None
        # o mais recente dos que entram é recent_dinner (-3min)
        assert result.id == report_dataset["recent_dinner"].id


# ===========================================================================
# list_recent_by_period
# ===========================================================================


class TestListRecentByPeriod:
    """
    list_recent_by_period filtra por dia no fuso America/Fortaleza (UTC-3).
    FROZEN_NOW = 25/12 14:00 UTC = 25/12 11:00 Fortaleza.

    Janela do dia 25/12 em Fortaleza:
      - início: 25/12 00:00 Fortaleza = 25/12 03:00 UTC
      - fim:    26/12 00:00 Fortaleza = 26/12 03:00 UTC

    Reports dentro do dia 25/12 Fortaleza:
      - recent_lunch_ip_a  (-5min  → 13:55 UTC = 10:55 Fortaleza) ✓
      - recent_lunch_ip_b  (-10min → 13:50 UTC = 10:50 Fortaleza) ✓
      - recent_dinner      (-3min  → 13:57 UTC = 10:57 Fortaleza) ✓
      - old_lunch          (-60min → 13:00 UTC = 10:00 Fortaleza) ✓
      - yesterday_lunch    (-26h   → 25/12 12:00 UTC = 24/12 09:00 Fortaleza) ✗
    """

    async def test_returns_lunch_reports_for_today(self, repo, report_dataset):
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=today_fortaleza,
        )

        result_ids = {r.id for r in result}
        # todos os lunches do dia 25/12 em Fortaleza devem estar presentes
        assert report_dataset["recent_lunch_ip_a"].id in result_ids
        assert report_dataset["recent_lunch_ip_b"].id in result_ids
        assert report_dataset["old_lunch"].id in result_ids

    async def test_excludes_yesterday_report(self, repo, report_dataset):
        """yesterday_lunch (-26h) está em 24/12 Fortaleza — não deve aparecer em 25/12."""
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=today_fortaleza,
        )

        result_ids = {r.id for r in result}
        assert report_dataset["yesterday_lunch"].id not in result_ids

    async def test_excludes_dinner_from_lunch_query(self, repo, report_dataset):
        """list_recent_by_period filtra por meal_period — DINNER não aparece em LUNCH."""
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=today_fortaleza,
        )

        result_ids = {r.id for r in result}
        assert report_dataset["recent_dinner"].id not in result_ids

    async def test_returns_dinner_reports_for_today(self, repo, report_dataset):
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.DINNER,
            day=today_fortaleza,
        )

        result_ids = {r.id for r in result}
        assert report_dataset["recent_dinner"].id in result_ids

    async def test_does_not_return_other_ru_reports(self, repo, report_dataset):
        """auroras_recent_lunch não deve aparecer na busca pelo ru_palmares."""
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()
        auroras_report = report_dataset["auroras_recent_lunch"]

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=today_fortaleza,
        )

        result_ids = {r.id for r in result}
        assert auroras_report.id not in result_ids

    async def test_returns_empty_list_for_date_without_reports(
        self, repo, report_dataset
    ):
        ru_id = report_dataset["ru_palmares"].id

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=datetime(2025, 1, 1).date(),
        )

        assert result == []

    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_recent_by_period(
            ru_id=999999,
            meal_period=MealPeriodEnum.LUNCH,
            day=datetime(2025, 12, 25).date(),
        )

        assert result == []

    async def test_limit_is_respected(self, repo, report_dataset):
        """Com limit=1 retorna apenas o mais recente."""
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=today_fortaleza,
            limit=1,
        )

        assert len(result) == 1
        # order_by created_at desc — o mais recente dos lunches de hoje é recent_lunch_ip_a (-5min)
        assert result[0].id == report_dataset["recent_lunch_ip_a"].id

    async def test_offset_is_respected(self, repo, report_dataset):
        """offset=1 pula o mais recente e retorna o segundo."""
        ru_id = report_dataset["ru_palmares"].id
        today_fortaleza = datetime(2025, 12, 25).date()

        result = await repo.list_recent_by_period(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            day=today_fortaleza,
            limit=1,
            offset=1,
        )

        assert len(result) == 1
        # segundo mais recente dos lunches de hoje é recent_lunch_ip_b (-10min)
        assert result[0].id == report_dataset["recent_lunch_ip_b"].id

    async def test_returns_list_type(self, repo, report_dataset):
        result = await repo.list_recent_by_period(
            ru_id=report_dataset["ru_palmares"].id,
            meal_period=MealPeriodEnum.LUNCH,
            day=datetime(2025, 12, 25).date(),
        )

        assert isinstance(result, list)


# ===========================================================================
# list_recent_by_period_within_minutes
# ===========================================================================


class TestListRecentByPeriodWithinMinutes:
    @freeze_time(FROZEN_NOW)
    async def test_returns_lunch_reports_within_window(self, repo, report_dataset):
        """
        Dentro de 15min a partir de FROZEN_NOW:
          - recent_lunch_ip_a (-5min)  ✓
          - recent_lunch_ip_b (-10min) ✓
          - old_lunch (-60min)         ✗
        """
        ru_id = report_dataset["ru_palmares"].id

        result = await repo.list_recent_by_period_within_minutes(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            minutes=15,
        )

        result_ids = {r.id for r in result}
        assert report_dataset["recent_lunch_ip_a"].id in result_ids
        assert report_dataset["recent_lunch_ip_b"].id in result_ids
        assert report_dataset["old_lunch"].id not in result_ids

    @freeze_time(FROZEN_NOW)
    async def test_excludes_dinner_from_lunch_window(self, repo, report_dataset):
        """recent_dinner é DINNER — não deve aparecer em busca por LUNCH."""
        ru_id = report_dataset["ru_palmares"].id

        result = await repo.list_recent_by_period_within_minutes(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            minutes=15,
        )

        result_ids = {r.id for r in result}
        assert report_dataset["recent_dinner"].id not in result_ids

    @freeze_time(FROZEN_NOW)
    async def test_returns_dinner_reports_within_window(self, repo, report_dataset):
        """recent_dinner (-3min) é DINNER e está dentro de 15min."""
        ru_id = report_dataset["ru_palmares"].id

        result = await repo.list_recent_by_period_within_minutes(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.DINNER,
            minutes=15,
        )

        result_ids = {r.id for r in result}
        assert report_dataset["recent_dinner"].id in result_ids

    @freeze_time(FROZEN_NOW)
    async def test_does_not_return_other_ru_reports(self, repo, report_dataset):
        """auroras_recent_lunch não deve aparecer na busca pelo ru_palmares."""
        ru_id = report_dataset["ru_palmares"].id
        auroras_report = report_dataset["auroras_recent_lunch"]

        result = await repo.list_recent_by_period_within_minutes(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            minutes=15,
        )

        result_ids = {r.id for r in result}
        assert auroras_report.id not in result_ids

    @freeze_time(FROZEN_NOW)
    async def test_returns_empty_list_when_no_reports_in_window(
        self, repo, report_dataset
    ):
        """Com janela de 1min, nenhum report de LUNCH está dentro."""
        ru_id = report_dataset["ru_palmares"].id

        result = await repo.list_recent_by_period_within_minutes(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
            minutes=1,
        )

        assert result == []

    @freeze_time(FROZEN_NOW)
    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_recent_by_period_within_minutes(
            ru_id=999999,
            meal_period=MealPeriodEnum.LUNCH,
            minutes=15,
        )

        assert result == []

    @freeze_time(FROZEN_NOW)
    async def test_returns_list_type(self, repo, report_dataset):
        result = await repo.list_recent_by_period_within_minutes(
            ru_id=report_dataset["ru_palmares"].id,
            meal_period=MealPeriodEnum.LUNCH,
            minutes=15,
        )

        assert isinstance(result, list)


# ===========================================================================
# count_within_minutes
# ===========================================================================


class TestCountWithinMinutes:
    @freeze_time(FROZEN_NOW)
    async def test_counts_all_reports_within_window(self, repo, report_dataset):
        """
        Dentro de 15min a partir de FROZEN_NOW:
          - recent_lunch_ip_a (-5min)      ✓ ru_palmares
          - recent_lunch_ip_b (-10min)     ✓ ru_palmares
          - recent_dinner (-3min)          ✓ ru_palmares
          - auroras_recent_lunch (-5min)   ✓ ru_auroras
          Total esperado: >= 4 (pode haver reports de outros testes ainda visíveis)
        """
        count = await repo.count_within_minutes(minutes=15)

        assert count >= 4

    @freeze_time(FROZEN_NOW)
    async def test_excludes_reports_outside_window(self, repo, report_dataset):
        """old_lunch (-60min) e yesterday_lunch (-26h) ficam fora de 15min."""
        count_15min = await repo.count_within_minutes(minutes=15)
        count_90min = await repo.count_within_minutes(minutes=90)

        # com 90min entra old_lunch também — count deve ser maior
        assert count_90min > count_15min

    @freeze_time(FROZEN_NOW)
    async def test_counts_across_all_restaurants(self, repo, report_dataset):
        """count_within_minutes não filtra por ru_id — conta todos os RUs."""
        # dentro de 15min: 3 de ru_palmares + 1 de ru_auroras = 4 do dataset
        count = await repo.count_within_minutes(minutes=15)

        # auroras_recent_lunch deve estar incluído
        assert count >= 4

    @freeze_time(FROZEN_NOW)
    async def test_returns_zero_for_empty_window(self, repo, report_dataset):
        """Com janela de 1min nenhum report do dataset está dentro."""
        count = await repo.count_within_minutes(minutes=1)

        assert count == 0

    @freeze_time(FROZEN_NOW)
    async def test_returns_integer(self, repo, report_dataset):
        count = await repo.count_within_minutes(minutes=15)

        assert isinstance(count, int)


# ===========================================================================
# count_today
# ===========================================================================


class TestCountToday:
    """
    count_today() conta reports do dia atual em America/Fortaleza (UTC-3).
    FROZEN_NOW = 25/12 14:00 UTC = 25/12 11:00 Fortaleza.

    Janela do dia 25/12 em Fortaleza:
      25/12 00:00 Fortaleza = 25/12 03:00 UTC  →  26/12 00:00 Fortaleza = 26/12 03:00 UTC

    Reports dentro do dia 25/12 Fortaleza (do dataset):
      - recent_lunch_ip_a  (-5min  → 13:55 UTC) ✓
      - recent_lunch_ip_b  (-10min → 13:50 UTC) ✓
      - recent_dinner      (-3min  → 13:57 UTC) ✓
      - old_lunch          (-60min → 13:00 UTC) ✓
      - auroras_recent_lunch (-5min → 13:55 UTC) ✓
      - yesterday_lunch    (-26h   → 24/12 09:00 Fortaleza) ✗
    """

    @freeze_time(FROZEN_NOW)
    async def test_counts_reports_from_today_in_fortaleza(self, repo, report_dataset):
        count = await repo.count_today()

        # dataset tem 5 reports no dia 25/12 Fortaleza
        assert count >= 5

    @freeze_time(FROZEN_NOW)
    async def test_excludes_yesterday_report(self, repo, report_dataset):
        """
        yesterday_lunch está em 24/12 Fortaleza.
        Compara count_today com e sem ele para confirmar exclusão.
        """
        count_today = await repo.count_today()

        # count_within_minutes com janela grande inclui yesterday_lunch
        count_all = await repo.count_within_minutes(minutes=60 * 30)

        # count_today deve ser menor que count_all (yesterday_lunch está excluído)
        assert count_today < count_all

    @freeze_time(FROZEN_NOW)
    async def test_counts_across_all_restaurants(self, repo, report_dataset):
        """count_today não filtra por ru_id — conta todos os RUs."""
        count = await repo.count_today()

        # dataset tem reports de ru_palmares e ru_auroras em 25/12 Fortaleza
        assert count >= 5

    @freeze_time(FROZEN_NOW)
    async def test_returns_integer(self, repo, report_dataset):
        count = await repo.count_today()

        assert isinstance(count, int)
