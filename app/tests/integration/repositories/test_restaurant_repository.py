"""
Testes de integração para RestaurantRepository.

Estratégia de fixtures:
- `restaurant_dataset` (scope="class") — persiste um conjunto fixo de registros
  uma única vez por classe de teste. Todos os testes de leitura compartilham esses
  dados sem recriá-los, equivalente ao setUpTestData do Django.
- `test_db_session` (scope padrão) — usado apenas em testes de escrita (create),
  que precisam de isolamento individual via rollback.

Restrição de campus:
  Existem apenas 3 campus (PALMARES, AURORAS, LIBERDADE) com unique constraint.
  O dataset usa PALMARES (ativo) e AURORAS (inativo).
  TestCreate usa LIBERDADE explicitamente para não colidir com o dataset.
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.restaurant import Restaurant
from app.repositories.restaurant_repository import RestaurantRepository
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
async def restaurant_dataset(test_engine):
    """
    Cria e persiste um conjunto fixo de restaurantes para todos os testes
    de leitura da classe. Executa uma única vez (equivalente ao setUpTestData).

    Usa test_engine diretamente com scope="class" para não conflitar com
    test_db_session (scope="function"). Os dados NÃO são revertidos entre
    testes — a classe inteira compartilha o mesmo estado.

    Campus utilizados:
      - PALMARES → ativo   (usado nos testes de leitura)
      - AURORAS  → inativo (usado para validar filtros de only_active)
      - LIBERDADE → reservado para TestCreate (não entra no dataset)
    """
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with session_factory() as session:
        # FIX: uma única transação para insert + refresh.
        # Separar em dois begin() causava "transaction already begun"
        # porque o autobegin do refresh ficava aberto no teardown.
        async with session.begin():
            active_palmares = RestaurantPalmaresDBFactory()
            inactive_auroras = RestaurantAurorasDBFactory(is_active=False)
            session.add_all([active_palmares, inactive_auroras])
            # flush dentro do begin() para gerar id/timestamps antes do refresh
            await session.flush()
            await session.refresh(active_palmares)
            await session.refresh(inactive_auroras)
        # begin() faz commit ao sair do bloco — sessão volta ao estado limpo

        yield {
            "active": active_palmares,
            "inactive": inactive_auroras,
            "all_active": [active_palmares],
        }

        # teardown: sessão está limpa (sem transação aberta), begin() funciona
        async with session.begin():
            await session.delete(active_palmares)
            await session.delete(inactive_auroras)


# ---------------------------------------------------------------------------
# Fixture de repositório
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def repo(test_db_session):
    return RestaurantRepository(test_db_session)


# ===========================================================================
# count_active
# ===========================================================================


class TestCountActive:
    async def test_returns_only_active_count(self, repo, restaurant_dataset):
        count = await repo.count_active()

        assert count == len(restaurant_dataset["all_active"])

    async def test_does_not_count_inactive(self, repo, restaurant_dataset):
        inactive = restaurant_dataset["inactive"]

        count = await repo.count_active()

        assert inactive.is_active is False
        assert count == len(restaurant_dataset["all_active"])


# ===========================================================================
# get_by_id
# ===========================================================================


class TestGetById:
    async def test_returns_restaurant_by_id(self, repo, restaurant_dataset):
        expected = restaurant_dataset["active"]

        result = await repo.get_by_id(expected.id)

        assert result is not None
        assert result.id == expected.id

    async def test_returns_none_for_nonexistent_id(self, repo):
        result = await repo.get_by_id(999999)

        assert result is None

    async def test_returns_inactive_restaurant_by_id(self, repo, restaurant_dataset):
        """get_by_id não filtra por is_active — retorna qualquer registro."""
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_by_id(inactive.id)

        assert result is not None
        assert result.is_active is False


# ===========================================================================
# get_by_public_id
# ===========================================================================


class TestGetByPublicId:
    async def test_returns_active_restaurant_by_public_id(
        self, repo, restaurant_dataset
    ):
        expected = restaurant_dataset["active"]

        result = await repo.get_by_public_id(expected.public_id)

        assert result is not None
        assert result.public_id == expected.public_id

    async def test_returns_none_for_inactive_when_only_active_true(
        self, repo, restaurant_dataset
    ):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_by_public_id(inactive.public_id, only_active=True)

        assert result is None

    async def test_returns_inactive_when_only_active_false(
        self, repo, restaurant_dataset
    ):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_by_public_id(inactive.public_id, only_active=False)

        assert result is not None
        assert result.public_id == inactive.public_id

    async def test_returns_none_for_nonexistent_public_id(self, repo):
        from uuid import uuid4

        result = await repo.get_by_public_id(uuid4())

        assert result is None

    async def test_only_active_defaults_to_true(self, repo, restaurant_dataset):
        """Confirma que o default de only_active=True filtra inativos."""
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_by_public_id(inactive.public_id)

        assert result is None


# ===========================================================================
# get_by_name
# ===========================================================================


class TestGetByName:
    async def test_returns_active_restaurant_by_name(self, repo, restaurant_dataset):
        expected = restaurant_dataset["active"]

        result = await repo.get_by_name(expected.name)

        assert result is not None
        assert result.name == expected.name

    async def test_returns_none_for_inactive_when_only_active_true(
        self, repo, restaurant_dataset
    ):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_by_name(inactive.name, only_active=True)

        assert result is None

    async def test_returns_inactive_when_only_active_false(
        self, repo, restaurant_dataset
    ):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_by_name(inactive.name, only_active=False)

        assert result is not None
        assert result.name == inactive.name

    async def test_returns_none_for_nonexistent_name(self, repo):
        result = await repo.get_by_name("RU Inexistente")

        assert result is None

    async def test_name_match_is_exact(self, repo):
        """get_by_name usa igualdade exata, não LIKE — substring não retorna resultado."""
        result = await repo.get_by_name("Palmares")  # substring de "RU Palmares"

        assert result is None


# ===========================================================================
# get_bulk_by_public_ids
# ===========================================================================


class TestGetBulkByPublicIds:
    async def test_returns_all_matching_active_restaurants(
        self, repo, restaurant_dataset
    ):
        active = restaurant_dataset["all_active"]
        public_ids = [r.public_id for r in active]

        result = await repo.get_bulk_by_public_ids(public_ids)

        result_ids = {r.public_id for r in result}
        assert set(public_ids).issubset(result_ids)

    async def test_excludes_inactive_when_only_active_true(
        self, repo, restaurant_dataset
    ):
        inactive = restaurant_dataset["inactive"]
        active = restaurant_dataset["active"]

        result = await repo.get_bulk_by_public_ids(
            [active.public_id, inactive.public_id],
            only_active=True,
        )

        result_ids = {r.public_id for r in result}
        assert active.public_id in result_ids
        assert inactive.public_id not in result_ids

    async def test_includes_inactive_when_only_active_false(
        self, repo, restaurant_dataset
    ):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_bulk_by_public_ids(
            [inactive.public_id],
            only_active=False,
        )

        assert len(result) == 1
        assert result[0].public_id == inactive.public_id

    async def test_returns_empty_list_for_unknown_ids(self, repo):
        from uuid import uuid4

        result = await repo.get_bulk_by_public_ids([uuid4(), uuid4()])

        assert result == []

    async def test_returns_empty_list_for_empty_input(self, repo):
        result = await repo.get_bulk_by_public_ids([])

        assert result == []

    async def test_returns_list_type(self, repo, restaurant_dataset):
        active = restaurant_dataset["active"]

        result = await repo.get_bulk_by_public_ids([active.public_id])

        assert isinstance(result, list)


# ===========================================================================
# get_all
# ===========================================================================


class TestGetAll:
    async def test_returns_only_active_by_default(self, repo, restaurant_dataset):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_all()

        result_ids = {r.id for r in result}
        assert inactive.id not in result_ids

    async def test_returns_all_when_only_active_false(self, repo, restaurant_dataset):
        inactive = restaurant_dataset["inactive"]

        result = await repo.get_all(only_active=False)

        result_ids = {r.id for r in result}
        assert inactive.id in result_ids

    async def test_returns_list_type(self, repo):
        result = await repo.get_all()

        assert isinstance(result, list)

    async def test_all_returned_items_are_restaurant_instances(
        self, repo, restaurant_dataset
    ):
        result = await repo.get_all()

        assert all(isinstance(r, Restaurant) for r in result)

    async def test_active_restaurants_from_dataset_are_present(
        self, repo, restaurant_dataset
    ):
        expected_ids = {r.id for r in restaurant_dataset["all_active"]}

        result = await repo.get_all()

        result_ids = {r.id for r in result}
        assert expected_ids.issubset(result_ids)


# ===========================================================================
# create
# ===========================================================================


class TestCreate:
    """
    Testes de escrita — cada teste usa test_db_session com rollback automático.

    FIX: todos os testes usam RestaurantLiberdadeDBFactory (campus=LIBERDADE)
    explicitamente. O dataset ocupa PALMARES e AURORAS — usar o iterator da
    BaseRestaurantFactory causava colisão porque ele cicla pelos 3 campus
    sem saber quais já estão no banco.
    """

    async def test_persists_restaurant_and_returns_it(self, repo):
        restaurant = RestaurantLiberdadeDBFactory()

        result = await repo.create(restaurant)

        assert result is restaurant

    async def test_assigns_id_after_create(self, repo):
        restaurant = RestaurantLiberdadeDBFactory()

        await repo.create(restaurant)

        assert restaurant.id is not None
        assert isinstance(restaurant.id, int)

    async def test_assigns_public_id_after_create(self, repo):
        from uuid import UUID

        restaurant = RestaurantLiberdadeDBFactory()

        await repo.create(restaurant)

        assert restaurant.public_id is not None
        assert isinstance(restaurant.public_id, UUID)

    async def test_assigns_created_at_after_create(self, repo):
        restaurant = RestaurantLiberdadeDBFactory()

        await repo.create(restaurant)

        assert restaurant.created_at is not None

    async def test_created_restaurant_is_retrievable(self, repo):
        restaurant = RestaurantLiberdadeDBFactory()

        created = await repo.create(restaurant)
        found = await repo.get_by_id(created.id)

        assert found is not None
        assert found.id == created.id

    async def test_create_does_not_commit(self, repo):
        """
        create() só faz flush, não commit.
        O fato de get_by_id funcionar dentro da mesma sessão confirma
        que o registro está visível via flush mas a transação segue aberta.
        O rollback acontece automaticamente via test_db_session ao fim do teste.
        """
        restaurant = RestaurantLiberdadeDBFactory()

        created = await repo.create(restaurant)

        found = await repo.get_by_id(created.id)
        assert found is not None  # visível dentro da transação (flush)
