"""
Testes de integração para RestaurantScheduleExceptionRepository.

Estratégia de fixtures:
- `exception_dataset` (scope="class") — persiste um conjunto fixo de exceções
  uma única vez por classe de teste, equivalente ao setUpTestData do Django.
- `test_db_session` (scope padrão) — usado nos testes de escrita (create),
  que precisam de isolamento individual via rollback.

Nota sobre unique constraints:
  - (ru_id, exception_date, meal_period) para exceções com período definido
  - Índice parcial (ru_id, exception_date) WHERE meal_period IS NULL para dia inteiro
  Cada combinação só pode existir uma vez por restaurante.
"""

from datetime import date
from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.restaurant import (
    ExceptionTypeEnum,
    MealPeriodEnum,
    RestaurantScheduleException,
)
from app.repositories.restaurant_schedule_exception_repository import (
    RestaurantScheduleExceptionRepository,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantAurorasDBFactory,
    RestaurantLiberdadeDBFactory,
    RestaurantPalmaresDBFactory,
    RestaurantScheduleExceptionDBFactory,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Dataset compartilhado — criado uma vez por classe
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="class", loop_scope="session")
async def exception_dataset(test_engine):
    """
    Persiste dois restaurantes e um conjunto de exceções com combinações distintas
    de exception_date, meal_period e exception_type.

    Restaurantes:
      - ru_palmares  → usado como RU principal dos testes
      - ru_auroras   → usado para validar que buscas por ru_id não cruzam restaurantes

    Mapa do dataset:
    ┌──────────────────────────────────┬────────────┬─────────────┬──────────────┐
    │ chave do dict                    │    data    │ meal_period │    type      │
    ├──────────────────────────────────┼────────────┼─────────────┼──────────────┤
    │ christmas_whole_day              │ 2025-12-25 │    None     │   CLOSED     │ ← dia inteiro
    │ christmas_lunch                  │ 2025-12-25 │    LUNCH    │   CLOSED     │
    │ new_year_dinner_custom           │ 2025-12-31 │   DINNER    │ CUSTOM_HOURS │
    │ carnival_lunch                   │ 2026-03-03 │    LUNCH    │   CLOSED     │
    │ auroras_christmas_whole_day      │ 2025-12-25 │    None     │   CLOSED     │ ← outro RU
    └──────────────────────────────────┴────────────┴─────────────┴──────────────┘
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

            # Natal — dia inteiro fechado (meal_period=None)
            christmas_whole_day = RestaurantScheduleExceptionDBFactory(
                ru_id=ru_palmares.id,
                exception_date=date(2025, 12, 25),
                exception_type=ExceptionTypeEnum.CLOSED,
                meal_period=None,
            )

            # Natal — apenas almoço fechado (mesmo dia, período diferente)
            christmas_lunch = RestaurantScheduleExceptionDBFactory(
                ru_id=ru_palmares.id,
                exception_date=date(2025, 12, 25),
                exception_type=ExceptionTypeEnum.CLOSED,
                meal_period=MealPeriodEnum.LUNCH,
            )

            # Véspera de Ano Novo — jantar com horário especial
            from datetime import time

            new_year_dinner_custom = RestaurantScheduleExceptionDBFactory(
                ru_id=ru_palmares.id,
                exception_date=date(2025, 12, 31),
                exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
                meal_period=MealPeriodEnum.DINNER,
                opens_at=time(17, 0),
                closes_at=time(19, 0),
            )

            # Carnaval — almoço fechado em data diferente
            carnival_lunch = RestaurantScheduleExceptionDBFactory(
                ru_id=ru_palmares.id,
                exception_date=date(2026, 3, 3),
                exception_type=ExceptionTypeEnum.CLOSED,
                meal_period=MealPeriodEnum.LUNCH,
            )

            # Auroras — Natal dia inteiro (mesmo dia que Palmares, RU diferente)
            auroras_christmas_whole_day = RestaurantScheduleExceptionDBFactory(
                ru_id=ru_auroras.id,
                exception_date=date(2025, 12, 25),
                exception_type=ExceptionTypeEnum.CLOSED,
                meal_period=None,
            )

            session.add_all(
                [
                    christmas_whole_day,
                    christmas_lunch,
                    new_year_dinner_custom,
                    carnival_lunch,
                    auroras_christmas_whole_day,
                ]
            )
            await session.flush()

            for obj in [
                christmas_whole_day,
                christmas_lunch,
                new_year_dinner_custom,
                carnival_lunch,
                auroras_christmas_whole_day,
            ]:
                await session.refresh(obj)

        yield {
            "ru_palmares": ru_palmares,
            "ru_auroras": ru_auroras,
            # exceções do ru_palmares
            "christmas_whole_day": christmas_whole_day,  # 25/12, None,   CLOSED
            "christmas_lunch": christmas_lunch,  # 25/12, LUNCH,  CLOSED
            "new_year_dinner_custom": new_year_dinner_custom,  # 31/12, DINNER, CUSTOM_HOURS
            "carnival_lunch": carnival_lunch,  # 03/03, LUNCH,  CLOSED
            # exceção do ru_auroras
            "auroras_christmas_whole_day": auroras_christmas_whole_day,
            # todas as exceções do ru_palmares
            "all_palmares": [
                christmas_whole_day,
                christmas_lunch,
                new_year_dinner_custom,
                carnival_lunch,
            ],
        }

        async with session.begin():
            for obj in [
                christmas_whole_day,
                christmas_lunch,
                new_year_dinner_custom,
                carnival_lunch,
                auroras_christmas_whole_day,
                ru_palmares,
                ru_auroras,
            ]:
                await session.delete(obj)


# ---------------------------------------------------------------------------
# Fixture de repositório
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def repo(test_db_session):
    return RestaurantScheduleExceptionRepository(test_db_session)


# ===========================================================================
# create
# ===========================================================================


class TestCreate:
    """
    Testes de escrita — isolados via rollback automático do test_db_session.
    Usa LIBERDADE para não colidir com o dataset (PALMARES e AURORAS).
    Cada teste usa uma data/meal_period diferente para evitar unique constraint.
    """

    @pytest_asyncio.fixture(scope="class", loop_scope="session")
    async def restaurant_for_create(self, test_engine):
        """Restaurante dedicado aos testes de create — criado uma vez para a classe."""
        session_factory = async_sessionmaker(
            bind=test_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        async with session_factory() as session:
            async with session.begin():
                restaurant = RestaurantLiberdadeDBFactory()
                session.add(restaurant)
                await session.flush()
                await session.refresh(restaurant)

            yield restaurant

            async with session.begin():
                await session.delete(restaurant)

    async def test_persists_exception_and_returns_it(self, repo, restaurant_for_create):
        exception = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant_for_create.id,
            exception_date=date(2025, 1, 1),
            meal_period=None,
        )

        result = await repo.create(exception)

        assert result is exception

    async def test_assigns_id_after_create(self, repo, restaurant_for_create):
        exception = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant_for_create.id,
            exception_date=date(2025, 2, 1),
            meal_period=MealPeriodEnum.LUNCH,
        )

        await repo.create(exception)

        assert exception.id is not None
        assert isinstance(exception.id, int)

    async def test_assigns_public_id_after_create(self, repo, restaurant_for_create):
        exception = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant_for_create.id,
            exception_date=date(2025, 3, 1),
            meal_period=MealPeriodEnum.DINNER,
        )

        await repo.create(exception)

        assert exception.public_id is not None
        assert isinstance(exception.public_id, UUID)

    async def test_assigns_created_at_after_create(self, repo, restaurant_for_create):
        exception = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant_for_create.id,
            exception_date=date(2025, 4, 1),
            meal_period=MealPeriodEnum.LUNCH,
        )

        await repo.create(exception)

        assert exception.created_at is not None

    async def test_created_exception_is_retrievable(self, repo, restaurant_for_create):
        exception = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant_for_create.id,
            exception_date=date(2025, 5, 1),
            meal_period=MealPeriodEnum.DINNER,
        )

        created = await repo.create(exception)
        found = await repo.get_by_public_id(created.public_id)

        assert found is not None
        assert found.id == created.id

    async def test_create_does_not_commit(self, repo, restaurant_for_create):
        """
        create() só faz flush, não commit.
        O registro é visível dentro da mesma transação via get_by_public_id,
        e o rollback automático do test_db_session desfaz ao fim do teste.
        """
        exception = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant_for_create.id,
            exception_date=date(2025, 6, 1),
            meal_period=None,
        )

        created = await repo.create(exception)

        # visível via flush dentro da transação ainda aberta
        found = await repo.get_by_public_id(created.public_id)
        assert found is not None


# ===========================================================================
# get_by_public_id
# ===========================================================================


class TestGetByPublicId:
    async def test_returns_exception_by_public_id(self, repo, exception_dataset):
        expected = exception_dataset["christmas_whole_day"]

        result = await repo.get_by_public_id(expected.public_id)

        assert result is not None
        assert result.public_id == expected.public_id

    async def test_returns_exception_with_meal_period(self, repo, exception_dataset):
        """get_by_public_id não filtra por meal_period — retorna qualquer exceção."""
        expected = exception_dataset["christmas_lunch"]

        result = await repo.get_by_public_id(expected.public_id)

        assert result is not None
        assert result.meal_period == MealPeriodEnum.LUNCH

    async def test_returns_exception_with_custom_hours(self, repo, exception_dataset):
        expected = exception_dataset["new_year_dinner_custom"]

        result = await repo.get_by_public_id(expected.public_id)

        assert result is not None
        assert result.exception_type == ExceptionTypeEnum.CUSTOM_HOURS

    async def test_returns_none_for_nonexistent_public_id(self, repo):
        from uuid import uuid4

        result = await repo.get_by_public_id(uuid4())

        assert result is None


# ===========================================================================
# list_by_ru_id
# ===========================================================================


class TestListByRuId:
    async def test_returns_all_exceptions_for_ru(self, repo, exception_dataset):
        ru_id = exception_dataset["ru_palmares"].id
        expected_ids = {e.id for e in exception_dataset["all_palmares"]}

        result = await repo.list_by_ru_id(ru_id)

        result_ids = {e.id for e in result}
        assert expected_ids.issubset(result_ids)

    async def test_does_not_return_other_ru_exceptions(self, repo, exception_dataset):
        """Exceções do ru_auroras não devem aparecer na busca pelo ru_palmares."""
        ru_id = exception_dataset["ru_palmares"].id
        auroras_exception = exception_dataset["auroras_christmas_whole_day"]

        result = await repo.list_by_ru_id(ru_id)

        result_ids = {e.id for e in result}
        assert auroras_exception.id not in result_ids

    async def test_returns_exceptions_with_null_meal_period(
        self, repo, exception_dataset
    ):
        """list_by_ru_id não filtra por meal_period — deve incluir exceções de dia inteiro."""
        ru_id = exception_dataset["ru_palmares"].id
        whole_day = exception_dataset["christmas_whole_day"]  # meal_period=None

        result = await repo.list_by_ru_id(ru_id)

        result_ids = {e.id for e in result}
        assert whole_day.id in result_ids

    async def test_returns_exceptions_across_multiple_dates(
        self, repo, exception_dataset
    ):
        """list_by_ru_id retorna exceções de todas as datas do RU."""
        ru_id = exception_dataset["ru_palmares"].id
        # dataset tem exceções em 25/12, 31/12 e 03/03
        christmas = exception_dataset["christmas_whole_day"]
        new_year = exception_dataset["new_year_dinner_custom"]
        carnival = exception_dataset["carnival_lunch"]

        result = await repo.list_by_ru_id(ru_id)

        result_ids = {e.id for e in result}
        assert christmas.id in result_ids
        assert new_year.id in result_ids
        assert carnival.id in result_ids

    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_by_ru_id(999999)

        assert result == []

    async def test_returns_list_type(self, repo, exception_dataset):
        result = await repo.list_by_ru_id(exception_dataset["ru_palmares"].id)

        assert isinstance(result, list)

    async def test_all_returned_items_are_exception_instances(
        self, repo, exception_dataset
    ):
        result = await repo.list_by_ru_id(exception_dataset["ru_palmares"].id)

        assert all(isinstance(e, RestaurantScheduleException) for e in result)


# ===========================================================================
# list_by_ru_id_and_date
# ===========================================================================


class TestListByRuIdAndDate:
    async def test_returns_all_exceptions_for_date(self, repo, exception_dataset):
        """
        25/12 tem duas exceções no ru_palmares:
        - christmas_whole_day (meal_period=None)
        - christmas_lunch (meal_period=LUNCH)
        """
        ru_id = exception_dataset["ru_palmares"].id
        christmas = date(2025, 12, 25)

        result = await repo.list_by_ru_id_and_date(ru_id, christmas)

        result_ids = {e.id for e in result}
        assert exception_dataset["christmas_whole_day"].id in result_ids
        assert exception_dataset["christmas_lunch"].id in result_ids

    async def test_does_not_return_exceptions_from_other_date(
        self, repo, exception_dataset
    ):
        """Busca por 25/12 não deve retornar exceções de 31/12 ou 03/03."""
        ru_id = exception_dataset["ru_palmares"].id
        christmas = date(2025, 12, 25)

        result = await repo.list_by_ru_id_and_date(ru_id, christmas)

        result_ids = {e.id for e in result}
        assert exception_dataset["new_year_dinner_custom"].id not in result_ids
        assert exception_dataset["carnival_lunch"].id not in result_ids

    async def test_does_not_return_other_ru_same_date(self, repo, exception_dataset):
        """
        ru_auroras também tem exceção em 25/12 —
        a busca pelo ru_palmares não deve incluí-la.
        """
        ru_id = exception_dataset["ru_palmares"].id
        christmas = date(2025, 12, 25)
        auroras_exception = exception_dataset["auroras_christmas_whole_day"]

        result = await repo.list_by_ru_id_and_date(ru_id, christmas)

        result_ids = {e.id for e in result}
        assert auroras_exception.id not in result_ids

    async def test_returns_single_exception_for_date_with_one_entry(
        self, repo, exception_dataset
    ):
        """31/12 tem apenas uma exceção no ru_palmares (new_year_dinner_custom)."""
        ru_id = exception_dataset["ru_palmares"].id
        new_year_eve = date(2025, 12, 31)

        result = await repo.list_by_ru_id_and_date(ru_id, new_year_eve)

        assert len(result) == 1
        assert result[0].id == exception_dataset["new_year_dinner_custom"].id

    async def test_returns_empty_list_for_date_without_exceptions(
        self, repo, exception_dataset
    ):
        ru_id = exception_dataset["ru_palmares"].id

        # 2025-07-09 não tem nenhuma exceção no dataset
        result = await repo.list_by_ru_id_and_date(ru_id, date(2025, 7, 9))

        assert result == []

    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_by_ru_id_and_date(999999, date(2025, 12, 25))

        assert result == []

    async def test_returns_list_type(self, repo, exception_dataset):
        result = await repo.list_by_ru_id_and_date(
            exception_dataset["ru_palmares"].id, date(2025, 12, 25)
        )

        assert isinstance(result, list)


# ===========================================================================
# get_by_ru_id_date_and_meal_period
# ===========================================================================


class TestGetByRuIdDateAndMealPeriod:
    async def test_returns_whole_day_exception_with_null_meal_period(
        self, repo, exception_dataset
    ):
        """meal_period=None representa exceção de dia inteiro."""
        ru_id = exception_dataset["ru_palmares"].id
        expected = exception_dataset["christmas_whole_day"]

        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 12, 25),
            meal_period=None,
        )

        assert result is not None
        assert result.id == expected.id

    async def test_returns_specific_period_exception(self, repo, exception_dataset):
        """meal_period=LUNCH retorna a exceção de almoço, não a de dia inteiro."""
        ru_id = exception_dataset["ru_palmares"].id
        expected = exception_dataset["christmas_lunch"]

        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 12, 25),
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert result is not None
        assert result.id == expected.id
        assert result.meal_period == MealPeriodEnum.LUNCH

    async def test_distinguishes_null_and_lunch_on_same_date(
        self, repo, exception_dataset
    ):
        """
        25/12 tem meal_period=None e meal_period=LUNCH —
        cada consulta deve retornar exatamente o registro do período solicitado.
        """
        ru_id = exception_dataset["ru_palmares"].id

        whole_day = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 12, 25),
            meal_period=None,
        )
        lunch_only = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 12, 25),
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert whole_day is not None
        assert lunch_only is not None
        assert whole_day.id != lunch_only.id
        assert whole_day.meal_period is None
        assert lunch_only.meal_period == MealPeriodEnum.LUNCH

    async def test_returns_custom_hours_exception(self, repo, exception_dataset):
        ru_id = exception_dataset["ru_palmares"].id
        expected = exception_dataset["new_year_dinner_custom"]

        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 12, 31),
            meal_period=MealPeriodEnum.DINNER,
        )

        assert result is not None
        assert result.id == expected.id
        assert result.exception_type == ExceptionTypeEnum.CUSTOM_HOURS

    async def test_returns_none_for_dinner_on_christmas(self, repo, exception_dataset):
        """
        25/12 tem None e LUNCH, mas não tem DINNER —
        a busca por DINNER deve retornar None.
        """
        ru_id = exception_dataset["ru_palmares"].id

        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 12, 25),
            meal_period=MealPeriodEnum.DINNER,
        )

        assert result is None

    async def test_returns_none_for_date_without_exceptions(
        self, repo, exception_dataset
    ):
        ru_id = exception_dataset["ru_palmares"].id

        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_id,
            exception_date=date(2025, 7, 9),
            meal_period=None,
        )

        assert result is None

    async def test_returns_none_for_unknown_ru_id(self, repo):
        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=999999,
            exception_date=date(2025, 12, 25),
            meal_period=None,
        )

        assert result is None

    async def test_does_not_return_other_ru_same_date_and_period(
        self, repo, exception_dataset
    ):
        """
        ru_auroras também tem exceção em 25/12 com meal_period=None —
        a busca pelo ru_palmares não deve retornar a do ru_auroras.
        """
        ru_palmares_id = exception_dataset["ru_palmares"].id
        auroras_exception = exception_dataset["auroras_christmas_whole_day"]

        result = await repo.get_by_ru_id_date_and_meal_period(
            ru_id=ru_palmares_id,
            exception_date=date(2025, 12, 25),
            meal_period=None,
        )

        assert result is not None
        assert result.id != auroras_exception.id
