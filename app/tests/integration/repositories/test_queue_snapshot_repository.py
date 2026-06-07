"""
Testes de integração para QueueSnapshotRepository.

Estratégia de fixtures:
- `snapshot_dataset` (scope="class") — persiste um conjunto fixo de snapshots
  uma única vez por classe de teste, equivalente ao setUpTestData do Django.
- `test_db_session` (scope padrão) — usado nos testes de escrita (create).

Particularidade do QueueSnapshot:
  PK composta (ru_id, meal_period) — cada restaurante tem exatamente 2 snapshots
  possíveis: (ru_id, LUNCH) e (ru_id, DINNER). Não há UUID nem id autoincrement.
  session.get() usa dicionário: {"ru_id": ..., "meal_period": ...}.

Estrutura do dataset:
  - ru_palmares → snapshot LUNCH + snapshot DINNER
  - ru_auroras  → snapshot LUNCH
  - ru_liberdade → reservado para TestCreate (não entra no dataset)
"""

from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.queue_snapshot import QueueSnapshot, SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.repositories.queue_snapshot_repository import QueueSnapshotRepository
from app.tests.factories.models.integration.queue_snapshot_model_factory import (
    QueueSnapshotDBFactory,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantAurorasDBFactory,
    RestaurantLiberdadeDBFactory,
    RestaurantPalmaresDBFactory,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Dataset compartilhado — criado uma vez por classe
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="class", loop_scope="session")
async def snapshot_dataset(test_engine):
    """
    Persiste 3 restaurantes e 3 snapshots para cobrir todos os métodos do repositório.

    Mapa do dataset:
    ┌──────────────────────────────┬──────────────┬─────────────┬───────────────┐
    │ chave                        │ restaurante  │ meal_period │ current_status│
    ├──────────────────────────────┼──────────────┼─────────────┼───────────────┤
    │ palmares_lunch               │ ru_palmares  │    LUNCH    │    SMALL      │
    │ palmares_dinner              │ ru_palmares  │   DINNER    │    MEDIUM     │
    │ auroras_lunch                │ ru_auroras   │    LUNCH    │    LARGE      │
    └──────────────────────────────┴──────────────┴─────────────┴───────────────┘

    ru_liberdade é criado mas não tem snapshots — reservado para TestCreate.
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
            ru_liberdade = RestaurantLiberdadeDBFactory()
            session.add_all([ru_palmares, ru_auroras, ru_liberdade])
            await session.flush()
            for obj in [ru_palmares, ru_auroras, ru_liberdade]:
                await session.refresh(obj)

            palmares_lunch = QueueSnapshotDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.LUNCH,
                current_status=SnapshotStatusEnum.SMALL,
                reports_last_15m=5,
                avg_status_value=Decimal("1.00"),
            )
            palmares_dinner = QueueSnapshotDBFactory(
                ru_id=ru_palmares.id,
                meal_period=MealPeriodEnum.DINNER,
                current_status=SnapshotStatusEnum.MEDIUM,
                reports_last_15m=3,
                avg_status_value=Decimal("2.00"),
            )
            auroras_lunch = QueueSnapshotDBFactory(
                ru_id=ru_auroras.id,
                meal_period=MealPeriodEnum.LUNCH,
                current_status=SnapshotStatusEnum.LARGE,
                reports_last_15m=10,
                avg_status_value=Decimal("3.00"),
            )

            session.add_all([palmares_lunch, palmares_dinner, auroras_lunch])
            await session.flush()
            for obj in [palmares_lunch, palmares_dinner, auroras_lunch]:
                await session.refresh(obj)

        yield {
            "ru_palmares": ru_palmares,
            "ru_auroras": ru_auroras,
            "ru_liberdade": ru_liberdade,
            "palmares_lunch": palmares_lunch,
            "palmares_dinner": palmares_dinner,
            "auroras_lunch": auroras_lunch,
            "all_snapshots": [palmares_lunch, palmares_dinner, auroras_lunch],
        }

        async with session.begin():
            for obj in [
                palmares_lunch,
                palmares_dinner,
                auroras_lunch,
                ru_palmares,
                ru_auroras,
                ru_liberdade,
            ]:
                await session.delete(obj)


# ---------------------------------------------------------------------------
# Fixture de repositório
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def repo(test_db_session):
    return QueueSnapshotRepository(test_db_session)


# ===========================================================================
# create
# ===========================================================================


class TestCreate:
    """
    Testes de escrita — isolados via rollback automático do test_db_session.
    Usa ru_liberdade (sem snapshots no dataset) para não colidir com o PK composto.
    Cada teste usa um meal_period diferente para não repetir a PK dentro da classe.
    """

    async def test_persists_snapshot_and_returns_it(self, repo, snapshot_dataset):
        snapshot = QueueSnapshotDBFactory(
            ru_id=snapshot_dataset["ru_liberdade"].id,
            meal_period=MealPeriodEnum.LUNCH,
        )

        result = await repo.create(snapshot)

        assert result is snapshot

    async def test_assigns_updated_at_after_create(self, repo, snapshot_dataset):
        snapshot = QueueSnapshotDBFactory(
            ru_id=snapshot_dataset["ru_liberdade"].id,
            meal_period=MealPeriodEnum.DINNER,
        )

        await repo.create(snapshot)

        assert snapshot.updated_at is not None

    async def test_created_snapshot_is_retrievable(self, repo, snapshot_dataset):
        """Após create(), get_by_ru_id_and_meal_period encontra o snapshot via flush."""
        ru_id = snapshot_dataset["ru_liberdade"].id
        snapshot = QueueSnapshotDBFactory(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.LUNCH,
        )

        await repo.create(snapshot)
        found = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.LUNCH)

        assert found is not None
        assert found.ru_id == ru_id
        assert found.meal_period == MealPeriodEnum.LUNCH

    async def test_create_does_not_commit(self, repo, snapshot_dataset):
        """
        create() só faz flush, não commit.
        O registro é visível dentro da mesma transação e desfeito pelo rollback
        automático do test_db_session ao fim do teste.
        """
        ru_id = snapshot_dataset["ru_liberdade"].id
        snapshot = QueueSnapshotDBFactory(
            ru_id=ru_id,
            meal_period=MealPeriodEnum.DINNER,
        )

        await repo.create(snapshot)

        # visível via flush na transação ainda aberta
        found = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.DINNER)
        assert found is not None

    async def test_stores_status_correctly(self, repo, snapshot_dataset):
        snapshot = QueueSnapshotDBFactory(
            ru_id=snapshot_dataset["ru_liberdade"].id,
            meal_period=MealPeriodEnum.LUNCH,
            current_status=SnapshotStatusEnum.FOOD_ENDED,
        )

        result = await repo.create(snapshot)

        assert result.current_status == SnapshotStatusEnum.FOOD_ENDED

    async def test_stores_reports_last_15m_correctly(self, repo, snapshot_dataset):
        snapshot = QueueSnapshotDBFactory(
            ru_id=snapshot_dataset["ru_liberdade"].id,
            meal_period=MealPeriodEnum.DINNER,
            reports_last_15m=42,
        )

        result = await repo.create(snapshot)

        assert result.reports_last_15m == 42


# ===========================================================================
# get_by_ru_id_and_meal_period
# ===========================================================================


class TestGetByRuIdAndMealPeriod:
    async def test_returns_lunch_snapshot_for_palmares(self, repo, snapshot_dataset):
        ru_id = snapshot_dataset["ru_palmares"].id
        expected = snapshot_dataset["palmares_lunch"]

        result = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.LUNCH)

        assert result is not None
        assert result.ru_id == expected.ru_id
        assert result.meal_period == expected.meal_period

    async def test_returns_dinner_snapshot_for_palmares(self, repo, snapshot_dataset):
        ru_id = snapshot_dataset["ru_palmares"].id
        expected = snapshot_dataset["palmares_dinner"]

        result = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.DINNER)

        assert result is not None
        assert result.ru_id == expected.ru_id
        assert result.meal_period == expected.meal_period

    async def test_distinguishes_lunch_from_dinner(self, repo, snapshot_dataset):
        """
        ru_palmares tem LUNCH e DINNER — cada consulta retorna
        exatamente o snapshot do período solicitado, não o outro.
        """
        ru_id = snapshot_dataset["ru_palmares"].id

        lunch = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.LUNCH)
        dinner = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.DINNER)

        assert lunch is not None
        assert dinner is not None
        assert lunch.meal_period == MealPeriodEnum.LUNCH
        assert dinner.meal_period == MealPeriodEnum.DINNER
        assert lunch.current_status != dinner.current_status

    async def test_returns_none_for_nonexistent_meal_period(
        self, repo, snapshot_dataset
    ):
        """ru_auroras tem apenas LUNCH — busca por DINNER deve retornar None."""
        ru_id = snapshot_dataset["ru_auroras"].id

        result = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.DINNER)

        assert result is None

    async def test_returns_none_for_unknown_ru_id(self, repo):
        result = await repo.get_by_ru_id_and_meal_period(999999, MealPeriodEnum.LUNCH)

        assert result is None

    async def test_does_not_return_other_ru_snapshot(self, repo, snapshot_dataset):
        """
        ru_palmares e ru_auroras têm LUNCH —
        a busca pelo ru_palmares não deve retornar o snapshot do ru_auroras.
        """
        ru_palmares_id = snapshot_dataset["ru_palmares"].id
        auroras_snapshot = snapshot_dataset["auroras_lunch"]

        result = await repo.get_by_ru_id_and_meal_period(
            ru_palmares_id, MealPeriodEnum.LUNCH
        )

        assert result is not None
        assert result.ru_id != auroras_snapshot.ru_id

    async def test_returned_snapshot_has_correct_status(self, repo, snapshot_dataset):
        ru_id = snapshot_dataset["ru_palmares"].id

        result = await repo.get_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.LUNCH)

        assert result.current_status == SnapshotStatusEnum.SMALL


# ===========================================================================
# get_bulk_by_ru_ids_and_meal_period
# ===========================================================================


class TestGetBulkByRuIdsAndMealPeriod:
    async def test_returns_snapshots_for_multiple_ru_ids(self, repo, snapshot_dataset):
        """ru_palmares e ru_auroras têm LUNCH — ambos devem ser retornados."""
        ru_ids = [
            snapshot_dataset["ru_palmares"].id,
            snapshot_dataset["ru_auroras"].id,
        ]

        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            ru_ids, MealPeriodEnum.LUNCH
        )

        result_ru_ids = {s.ru_id for s in result}
        assert snapshot_dataset["ru_palmares"].id in result_ru_ids
        assert snapshot_dataset["ru_auroras"].id in result_ru_ids

    async def test_filters_by_meal_period(self, repo, snapshot_dataset):
        """
        get_bulk retorna apenas o meal_period solicitado.
        ru_palmares tem LUNCH e DINNER — buscando LUNCH, DINNER não deve aparecer.
        """
        ru_ids = [snapshot_dataset["ru_palmares"].id]

        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            ru_ids, MealPeriodEnum.LUNCH
        )

        assert all(s.meal_period == MealPeriodEnum.LUNCH for s in result)

    async def test_excludes_ru_without_snapshot_for_period(
        self, repo, snapshot_dataset
    ):
        """
        ru_auroras não tem DINNER — passar seu id em busca por DINNER
        não deve retornar nenhum snapshot para ele.
        """
        ru_ids = [
            snapshot_dataset["ru_palmares"].id,
            snapshot_dataset["ru_auroras"].id,
        ]

        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            ru_ids, MealPeriodEnum.DINNER
        )

        # apenas ru_palmares tem DINNER
        result_ru_ids = {s.ru_id for s in result}
        assert snapshot_dataset["ru_palmares"].id in result_ru_ids
        assert snapshot_dataset["ru_auroras"].id not in result_ru_ids

    async def test_returns_empty_list_for_unknown_ru_ids(self, repo):
        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            [999998, 999999], MealPeriodEnum.LUNCH
        )

        assert result == []

    async def test_returns_empty_list_for_empty_input(self, repo):
        result = await repo.get_bulk_by_ru_ids_and_meal_period([], MealPeriodEnum.LUNCH)

        assert result == []

    async def test_returns_list_type(self, repo, snapshot_dataset):
        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            [snapshot_dataset["ru_palmares"].id], MealPeriodEnum.LUNCH
        )

        assert isinstance(result, list)

    async def test_all_returned_items_are_snapshot_instances(
        self, repo, snapshot_dataset
    ):
        ru_ids = [
            snapshot_dataset["ru_palmares"].id,
            snapshot_dataset["ru_auroras"].id,
        ]

        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            ru_ids, MealPeriodEnum.LUNCH
        )

        assert all(isinstance(s, QueueSnapshot) for s in result)

    async def test_single_ru_id_returns_one_snapshot(self, repo, snapshot_dataset):
        ru_ids = [snapshot_dataset["ru_palmares"].id]

        result = await repo.get_bulk_by_ru_ids_and_meal_period(
            ru_ids, MealPeriodEnum.LUNCH
        )

        assert len(result) == 1
        assert result[0].ru_id == snapshot_dataset["ru_palmares"].id


# ===========================================================================
# list_all
# ===========================================================================


class TestListAll:
    async def test_returns_all_snapshots(self, repo, snapshot_dataset):
        """list_all deve conter todos os 3 snapshots do dataset."""
        expected_pks = {
            (s.ru_id, s.meal_period) for s in snapshot_dataset["all_snapshots"]
        }

        result = await repo.list_all()

        result_pks = {(s.ru_id, s.meal_period) for s in result}
        assert expected_pks.issubset(result_pks)

    async def test_returns_snapshots_from_all_restaurants(self, repo, snapshot_dataset):
        """list_all não filtra por ru_id — retorna snapshots de todos os RUs."""
        result = await repo.list_all()

        result_ru_ids = {s.ru_id for s in result}
        assert snapshot_dataset["ru_palmares"].id in result_ru_ids
        assert snapshot_dataset["ru_auroras"].id in result_ru_ids

    async def test_returns_snapshots_from_all_periods(self, repo, snapshot_dataset):
        """list_all não filtra por meal_period — retorna LUNCH e DINNER."""
        result = await repo.list_all()

        # ru_palmares tem LUNCH e DINNER no dataset
        palmares_id = snapshot_dataset["ru_palmares"].id
        palmares_snapshots = [s for s in result if s.ru_id == palmares_id]
        periods = {s.meal_period for s in palmares_snapshots}

        assert MealPeriodEnum.LUNCH in periods
        assert MealPeriodEnum.DINNER in periods

    async def test_returns_list_type(self, repo):
        result = await repo.list_all()

        assert isinstance(result, list)

    async def test_all_returned_items_are_snapshot_instances(self, repo):
        result = await repo.list_all()

        assert all(isinstance(s, QueueSnapshot) for s in result)
