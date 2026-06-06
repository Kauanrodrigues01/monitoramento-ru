"""
Testes de integração para RestaurantScheduleRepository.

Estratégia de fixtures:
- `schedule_dataset` (scope="class") — persiste um conjunto fixo de schedules
  uma única vez por classe de teste, equivalente ao setUpTestData do Django.
- `test_db_session` (scope padrão) — usado nos testes de escrita (create),
  que precisam de isolamento individual via rollback.

Estrutura do dataset:
  - 1 restaurante (LIBERDADE) compartilhado por toda a suite
  - schedules variados cobrindo weekdays, meal_periods e is_active
  - PALMARES e AURORAS reservados caso outros testes precisem de RUs extras
"""

from uuid import UUID

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.restaurant import MealPeriodEnum, RestaurantSchedule
from app.repositories.restaurant_schedule_repository import (
    RestaurantScheduleRepository,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantLiberdadeDBFactory,
    RestaurantScheduleDBFactory,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Dataset compartilhado — criado uma vez por classe
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="class", loop_scope="session")
async def schedule_dataset(test_engine):
    """
    Persiste um restaurante (LIBERDADE) e 5 schedules com combinações distintas
    de weekday, meal_period e is_active para cobrir todos os métodos do repositório.

    Mapa do dataset:
    ┌─────────────────────────────┬─────────┬─────────────┬───────────┐
    │ chave do dict               │ weekday │ meal_period │ is_active │
    ├─────────────────────────────┼─────────┼─────────────┼───────────┤
    │ monday_lunch_active         │    0    │    LUNCH    │   True    │
    │ monday_dinner_active        │    0    │   DINNER    │   True    │
    │ tuesday_lunch_active        │    1    │    LUNCH    │   True    │
    │ tuesday_dinner_inactive     │    1    │   DINNER    │   False   │  ← único inativo
    │ wednesday_dinner_active     │    2    │   DINNER    │   True    │
    └─────────────────────────────┴─────────┴─────────────┴───────────┘

    Nota sobre tuesday_dinner_inactive:
      O unique constraint (ru_id, weekday, meal_period) impede dois schedules
      com a mesma combinação independente de is_active. Por isso o inativo usa
      DINNER (terça) — o slot de LUNCH na terça já está ocupado pelo ativo.
    """
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

            ru_id = restaurant.id

            # weekday=0 (segunda): dois períodos ativos para testar distinção por meal_period
            monday_lunch_active = RestaurantScheduleDBFactory(
                ru_id=ru_id,
                weekday=0,
                meal_period=MealPeriodEnum.LUNCH,
                is_active=True,
            )
            monday_dinner_active = RestaurantScheduleDBFactory(
                ru_id=ru_id,
                weekday=0,
                meal_period=MealPeriodEnum.DINNER,
                is_active=True,
            )

            # weekday=1 (terça): um ativo e um inativo em períodos distintos
            tuesday_lunch_active = RestaurantScheduleDBFactory(
                ru_id=ru_id,
                weekday=1,
                meal_period=MealPeriodEnum.LUNCH,
                is_active=True,
            )
            tuesday_dinner_inactive = RestaurantScheduleDBFactory(
                ru_id=ru_id,
                weekday=1,
                meal_period=MealPeriodEnum.DINNER,
                is_active=False,
            )

            # weekday=2 (quarta): apenas dinner ativo para testar filtro por weekday
            wednesday_dinner_active = RestaurantScheduleDBFactory(
                ru_id=ru_id,
                weekday=2,
                meal_period=MealPeriodEnum.DINNER,
                is_active=True,
            )

            session.add_all(
                [
                    monday_lunch_active,
                    monday_dinner_active,
                    tuesday_lunch_active,
                    tuesday_dinner_inactive,
                    wednesday_dinner_active,
                ]
            )
            await session.flush()

            for obj in [
                monday_lunch_active,
                monday_dinner_active,
                tuesday_lunch_active,
                tuesday_dinner_inactive,
                wednesday_dinner_active,
            ]:
                await session.refresh(obj)

        yield {
            "restaurant": restaurant,
            "ru_id": ru_id,
            "monday_lunch_active": monday_lunch_active,
            "monday_dinner_active": monday_dinner_active,
            "tuesday_lunch_active": tuesday_lunch_active,
            "tuesday_dinner_inactive": tuesday_dinner_inactive,
            "wednesday_dinner_active": wednesday_dinner_active,
            # todos os schedules ativos do dataset
            "all_active": [
                monday_lunch_active,
                monday_dinner_active,
                tuesday_lunch_active,
                wednesday_dinner_active,
            ],
        }

        async with session.begin():
            for obj in [
                monday_lunch_active,
                monday_dinner_active,
                tuesday_lunch_active,
                tuesday_dinner_inactive,
                wednesday_dinner_active,
                restaurant,
            ]:
                await session.delete(obj)


# ---------------------------------------------------------------------------
# Fixture de repositório
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
def repo(test_db_session):
    return RestaurantScheduleRepository(test_db_session)


# ===========================================================================
# create
# ===========================================================================


class TestCreate:
    """
    Testes de escrita — isolados via rollback automático do test_db_session.

    Usa um restaurante próprio (PALMARES) para não colidir com o dataset (LIBERDADE).
    Cada teste cria um schedule em um weekday/meal_period diferente para evitar
    conflito de unique constraint entre testes da mesma classe.
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

    async def test_persists_schedule_and_returns_it(self, repo, restaurant_for_create):
        # weekday=0, LUNCH — slot livre para o restaurante de create
        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant_for_create.id,
            weekday=0,
            meal_period=MealPeriodEnum.LUNCH,
        )

        result = await repo.create(schedule)

        assert result is schedule

    async def test_assigns_id_after_create(self, repo, restaurant_for_create):
        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant_for_create.id,
            weekday=1,
            meal_period=MealPeriodEnum.DINNER,
        )

        await repo.create(schedule)

        assert schedule.id is not None
        assert isinstance(schedule.id, int)

    async def test_assigns_public_id_after_create(self, repo, restaurant_for_create):
        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant_for_create.id,
            weekday=2,
            meal_period=MealPeriodEnum.LUNCH,
        )

        await repo.create(schedule)

        assert schedule.public_id is not None
        assert isinstance(schedule.public_id, UUID)

    async def test_assigns_created_at_after_create(self, repo, restaurant_for_create):
        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant_for_create.id,
            weekday=3,
            meal_period=MealPeriodEnum.LUNCH,
        )

        await repo.create(schedule)

        assert schedule.created_at is not None

    async def test_created_schedule_is_retrievable(self, repo, restaurant_for_create):
        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant_for_create.id,
            weekday=4,
            meal_period=MealPeriodEnum.DINNER,
        )

        created = await repo.create(schedule)
        found = await repo.get_by_public_id(created.public_id, only_active=True)

        assert found is not None
        assert found.id == created.id

    async def test_create_does_not_commit(self, repo, restaurant_for_create):
        """
        create() só faz flush, não commit.
        O registro é visível dentro da mesma transação via get_by_public_id,
        e o rollback automático do test_db_session desfaz ao fim do teste.
        """
        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant_for_create.id,
            weekday=5,
            meal_period=MealPeriodEnum.LUNCH,
        )

        created = await repo.create(schedule)

        # visível via flush dentro da transação ainda aberta
        found = await repo.get_by_public_id(created.public_id, only_active=True)
        assert found is not None


# ===========================================================================
# get_by_public_id
# ===========================================================================


class TestGetByPublicId:
    async def test_returns_active_schedule_by_public_id(self, repo, schedule_dataset):
        expected = schedule_dataset["monday_lunch_active"]

        result = await repo.get_by_public_id(expected.public_id)

        assert result is not None
        assert result.public_id == expected.public_id

    async def test_returns_none_for_inactive_when_only_active_true(
        self, repo, schedule_dataset
    ):
        # tuesday_dinner_inactive é o único inativo no dataset
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.get_by_public_id(inactive.public_id, only_active=True)

        assert result is None

    async def test_returns_inactive_when_only_active_false(
        self, repo, schedule_dataset
    ):
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.get_by_public_id(inactive.public_id, only_active=False)

        assert result is not None
        assert result.public_id == inactive.public_id

    async def test_only_active_defaults_to_true(self, repo, schedule_dataset):
        """Confirma que o default de only_active=True filtra inativos."""
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        # chamada sem only_active explícito — deve filtrar o inativo
        result = await repo.get_by_public_id(inactive.public_id)

        assert result is None

    async def test_returns_none_for_nonexistent_public_id(self, repo):
        from uuid import uuid4

        result = await repo.get_by_public_id(uuid4())

        assert result is None


# ===========================================================================
# list_by_ru_id
# ===========================================================================


class TestListByRuId:
    async def test_returns_all_active_schedules_for_ru(self, repo, schedule_dataset):
        ru_id = schedule_dataset["ru_id"]
        expected_ids = {s.id for s in schedule_dataset["all_active"]}

        result = await repo.list_by_ru_id(ru_id)

        result_ids = {s.id for s in result}
        assert expected_ids.issubset(result_ids)

    async def test_excludes_inactive_when_only_active_true(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id(ru_id, only_active=True)

        result_ids = {s.id for s in result}
        assert inactive.id not in result_ids

    async def test_includes_inactive_when_only_active_false(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id(ru_id, only_active=False)

        result_ids = {s.id for s in result}
        assert inactive.id in result_ids

    async def test_only_active_defaults_to_true(self, repo, schedule_dataset):
        """Confirma que o default filtra inativos sem passar only_active explícito."""
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id(ru_id)

        result_ids = {s.id for s in result}
        assert inactive.id not in result_ids

    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_by_ru_id(999999)

        assert result == []

    async def test_returns_list_type(self, repo, schedule_dataset):
        result = await repo.list_by_ru_id(schedule_dataset["ru_id"])

        assert isinstance(result, list)

    async def test_all_returned_items_are_schedule_instances(
        self, repo, schedule_dataset
    ):
        result = await repo.list_by_ru_id(schedule_dataset["ru_id"])

        assert all(isinstance(s, RestaurantSchedule) for s in result)


# ===========================================================================
# list_by_ru_id_and_meal_period
# ===========================================================================


class TestListByRuIdAndMealPeriod:
    async def test_returns_lunch_schedules(self, repo, schedule_dataset):
        ru_id = schedule_dataset["ru_id"]

        result = await repo.list_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.LUNCH)

        # dataset tem monday_lunch_active e tuesday_lunch_active como LUNCH ativos
        result_ids = {s.id for s in result}
        assert schedule_dataset["monday_lunch_active"].id in result_ids
        assert schedule_dataset["tuesday_lunch_active"].id in result_ids

    async def test_returns_dinner_schedules(self, repo, schedule_dataset):
        ru_id = schedule_dataset["ru_id"]

        result = await repo.list_by_ru_id_and_meal_period(ru_id, MealPeriodEnum.DINNER)

        # dataset tem monday_dinner_active e wednesday_dinner_active como DINNER ativos
        result_ids = {s.id for s in result}
        assert schedule_dataset["monday_dinner_active"].id in result_ids
        assert schedule_dataset["wednesday_dinner_active"].id in result_ids

    async def test_does_not_return_other_meal_period(self, repo, schedule_dataset):
        """LUNCH não retorna schedules de DINNER e vice-versa."""
        ru_id = schedule_dataset["ru_id"]

        lunch_result = await repo.list_by_ru_id_and_meal_period(
            ru_id, MealPeriodEnum.LUNCH
        )
        lunch_ids = {s.id for s in lunch_result}

        # schedules de DINNER não devem aparecer na busca por LUNCH
        assert schedule_dataset["monday_dinner_active"].id not in lunch_ids
        assert schedule_dataset["wednesday_dinner_active"].id not in lunch_ids

    async def test_excludes_inactive_when_only_active_true(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        # tuesday_dinner_inactive é DINNER com is_active=False
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id_and_meal_period(
            ru_id, MealPeriodEnum.DINNER, only_active=True
        )

        result_ids = {s.id for s in result}
        assert inactive.id not in result_ids

    async def test_includes_inactive_when_only_active_false(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id_and_meal_period(
            ru_id, MealPeriodEnum.DINNER, only_active=False
        )

        result_ids = {s.id for s in result}
        assert inactive.id in result_ids

    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_by_ru_id_and_meal_period(999999, MealPeriodEnum.LUNCH)

        assert result == []

    async def test_returns_list_type(self, repo, schedule_dataset):
        result = await repo.list_by_ru_id_and_meal_period(
            schedule_dataset["ru_id"], MealPeriodEnum.LUNCH
        )

        assert isinstance(result, list)


# ===========================================================================
# list_by_ru_id_and_weekday
# ===========================================================================


class TestListByRuIdAndWeekday:
    async def test_returns_both_periods_for_monday(self, repo, schedule_dataset):
        """weekday=0 (segunda) tem LUNCH e DINNER ativos — ambos devem retornar."""
        ru_id = schedule_dataset["ru_id"]

        result = await repo.list_by_ru_id_and_weekday(ru_id, weekday=0)

        result_ids = {s.id for s in result}
        assert schedule_dataset["monday_lunch_active"].id in result_ids
        assert schedule_dataset["monday_dinner_active"].id in result_ids

    async def test_does_not_return_other_weekday(self, repo, schedule_dataset):
        """Busca por segunda não retorna schedules de terça ou quarta."""
        ru_id = schedule_dataset["ru_id"]

        result = await repo.list_by_ru_id_and_weekday(ru_id, weekday=0)

        result_ids = {s.id for s in result}
        assert schedule_dataset["tuesday_lunch_active"].id not in result_ids
        assert schedule_dataset["wednesday_dinner_active"].id not in result_ids

    async def test_excludes_inactive_when_only_active_true(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        # tuesday_dinner_inactive está em weekday=1 com is_active=False
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id_and_weekday(
            ru_id, weekday=1, only_active=True
        )

        result_ids = {s.id for s in result}
        assert inactive.id not in result_ids

    async def test_includes_inactive_when_only_active_false(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.list_by_ru_id_and_weekday(
            ru_id, weekday=1, only_active=False
        )

        result_ids = {s.id for s in result}
        assert inactive.id in result_ids

    async def test_only_active_defaults_to_true(self, repo, schedule_dataset):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        # chamada sem only_active explícito — deve filtrar o inativo
        result = await repo.list_by_ru_id_and_weekday(ru_id, weekday=1)

        result_ids = {s.id for s in result}
        assert inactive.id not in result_ids

    async def test_returns_empty_list_for_weekday_with_no_schedules(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]

        # weekday=5 (sábado) não tem nenhum schedule no dataset
        result = await repo.list_by_ru_id_and_weekday(ru_id, weekday=5)

        assert result == []

    async def test_returns_empty_list_for_unknown_ru_id(self, repo):
        result = await repo.list_by_ru_id_and_weekday(999999, weekday=0)

        assert result == []

    async def test_returns_list_type(self, repo, schedule_dataset):
        result = await repo.list_by_ru_id_and_weekday(
            schedule_dataset["ru_id"], weekday=0
        )

        assert isinstance(result, list)


# ===========================================================================
# get_by_ru_id_weekday_and_meal_period
# ===========================================================================


class TestGetByRuIdWeekdayAndMealPeriod:
    async def test_returns_correct_schedule(self, repo, schedule_dataset):
        ru_id = schedule_dataset["ru_id"]
        expected = schedule_dataset["monday_lunch_active"]

        result = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id,
            weekday=0,
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert result is not None
        assert result.id == expected.id

    async def test_distinguishes_meal_period_on_same_weekday(
        self, repo, schedule_dataset
    ):
        """
        weekday=0 (segunda) tem LUNCH e DINNER — cada consulta deve retornar
        exatamente o schedule do período solicitado, não o outro.
        """
        ru_id = schedule_dataset["ru_id"]

        lunch = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id, weekday=0, meal_period=MealPeriodEnum.LUNCH
        )
        dinner = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id, weekday=0, meal_period=MealPeriodEnum.DINNER
        )

        assert lunch is not None
        assert dinner is not None
        assert lunch.id != dinner.id
        assert lunch.meal_period == MealPeriodEnum.LUNCH
        assert dinner.meal_period == MealPeriodEnum.DINNER

    async def test_returns_none_for_inactive_when_only_active_true(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        # tuesday_dinner_inactive: weekday=1, DINNER, is_active=False
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id,
            weekday=inactive.weekday,
            meal_period=inactive.meal_period,
            only_active=True,
        )

        assert result is None

    async def test_returns_inactive_when_only_active_false(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        result = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id,
            weekday=inactive.weekday,
            meal_period=inactive.meal_period,
            only_active=False,
        )

        assert result is not None
        assert result.id == inactive.id

    async def test_only_active_defaults_to_true(self, repo, schedule_dataset):
        ru_id = schedule_dataset["ru_id"]
        inactive = schedule_dataset["tuesday_dinner_inactive"]

        # chamada sem only_active explícito — deve filtrar o inativo
        result = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id,
            weekday=inactive.weekday,
            meal_period=inactive.meal_period,
        )

        assert result is None

    async def test_returns_none_for_weekday_without_schedule(
        self, repo, schedule_dataset
    ):
        ru_id = schedule_dataset["ru_id"]

        # weekday=5 (sábado) não tem nenhum schedule no dataset
        result = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=ru_id,
            weekday=5,
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert result is None

    async def test_returns_none_for_unknown_ru_id(self, repo):
        result = await repo.get_by_ru_id_weekday_and_meal_period(
            ru_id=999999,
            weekday=0,
            meal_period=MealPeriodEnum.LUNCH,
        )

        assert result is None
