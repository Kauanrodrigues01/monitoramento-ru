from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.queue_snapshot import QueueSnapshot, SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.tests.factories.models.integration.queue_snapshot_model_factory import (
    QueueSnapshotDBFactory,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantAurorasDBFactory,
    RestaurantPalmaresDBFactory,
)
from app.tests.integration.helpers import persist

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ===========================================================================
# QueueSnapshot — Criação e campos básicos
# ===========================================================================


class TestQueueSnapshotCreation:
    async def test_creates_with_required_fields(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        assert snapshot.ru_id == restaurant.id

    async def test_composite_pk_is_ru_id_and_meal_period(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, snapshot)

        # recupera pelo PK composto para confirmar que funciona como chave
        result = await test_db_session.get(
            QueueSnapshot,
            {"ru_id": restaurant.id, "meal_period": MealPeriodEnum.LUNCH},
        )
        assert result is not None

    async def test_two_snapshots_per_restaurant_lunch_and_dinner(self, test_db_session):
        """Cada restaurante tem exatamente uma linha por período."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        lunch = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        dinner = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
        )
        await persist(test_db_session, lunch, dinner)

        assert lunch.ru_id == dinner.ru_id
        assert lunch.meal_period != dinner.meal_period

    async def test_duplicate_composite_pk_raises(self, test_db_session):
        """PK composto (ru_id, meal_period) não pode se repetir."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        s1 = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, s1)

        s2 = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        test_db_session.add(s2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_updated_at_is_set_automatically(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        assert snapshot.updated_at is not None

    async def test_invalid_ru_id_raises(self, test_db_session):
        """FK constraint: ru_id deve referenciar um restaurant existente."""
        snapshot = QueueSnapshotDBFactory(ru_id=999999)
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()


# ===========================================================================
# QueueSnapshot — current_status
# ===========================================================================


class TestQueueSnapshotCurrentStatus:
    async def test_default_status_is_no_data(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        assert snapshot.current_status == SnapshotStatusEnum.NO_DATA

    async def test_stores_status_no_queue(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            current_status=SnapshotStatusEnum.NO_QUEUE,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.current_status == SnapshotStatusEnum.NO_QUEUE

    async def test_stores_status_small(self, test_db_session):
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.LUNCH,
            current_status=SnapshotStatusEnum.SMALL,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.current_status == SnapshotStatusEnum.SMALL

    async def test_stores_status_medium(self, test_db_session):
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            current_status=SnapshotStatusEnum.MEDIUM,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.current_status == SnapshotStatusEnum.MEDIUM

    async def test_stores_status_large(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            current_status=SnapshotStatusEnum.LARGE,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.current_status == SnapshotStatusEnum.LARGE

    async def test_stores_status_food_ended(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            current_status=SnapshotStatusEnum.FOOD_ENDED,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.current_status == SnapshotStatusEnum.FOOD_ENDED


# ===========================================================================
# QueueSnapshot — avg_status_value
# ===========================================================================


class TestQueueSnapshotAvgStatusValue:
    async def test_avg_status_value_is_nullable(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            avg_status_value=None,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.avg_status_value is None

    async def test_stores_minimum_valid_avg_status_value(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            avg_status_value=Decimal("0.00"),
        )
        await persist(test_db_session, snapshot)

        assert snapshot.avg_status_value == Decimal("0.00")

    async def test_stores_maximum_valid_avg_status_value(self, test_db_session):
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            avg_status_value=Decimal("3.00"),
        )
        await persist(test_db_session, snapshot)

        assert snapshot.avg_status_value == Decimal("3.00")

    async def test_stores_mid_range_avg_status_value(self, test_db_session):
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            avg_status_value=Decimal("1.50"),
        )
        await persist(test_db_session, snapshot)

        assert snapshot.avg_status_value == Decimal("1.50")

    async def test_avg_status_value_above_maximum_raises(self, test_db_session):
        """Check constraint: avg_status_value <= 3.00."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            avg_status_value=Decimal("3.01"),
        )
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_avg_status_value_below_minimum_raises(self, test_db_session):
        """Check constraint: avg_status_value >= 0.00."""
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            avg_status_value=Decimal("-0.01"),
        )
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()


# ===========================================================================
# QueueSnapshot — reports_last_15m
# ===========================================================================


class TestQueueSnapshotReportsLast15m:
    async def test_default_reports_last_15m_is_zero(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        assert snapshot.reports_last_15m == 0

    async def test_stores_positive_reports_last_15m(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            reports_last_15m=42,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.reports_last_15m == 42

    async def test_negative_reports_last_15m_raises(self, test_db_session):
        """Check constraint: reports_last_15m >= 0."""
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            reports_last_15m=-1,
        )
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()


# ===========================================================================
# QueueSnapshot — confidence_score
# ===========================================================================


class TestQueueSnapshotConfidenceScore:
    async def test_default_confidence_score_is_one(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        assert snapshot.confidence_score == Decimal("1.00")

    async def test_stores_minimum_valid_confidence_score(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            confidence_score=Decimal("0.05"),
        )
        await persist(test_db_session, snapshot)

        assert snapshot.confidence_score == Decimal("0.05")

    async def test_stores_maximum_valid_confidence_score(self, test_db_session):
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("1.00"),
        )
        await persist(test_db_session, snapshot)

        assert snapshot.confidence_score == Decimal("1.00")

    async def test_confidence_score_below_minimum_raises(self, test_db_session):
        """Check constraint: confidence_score >= 0.05."""
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            confidence_score=Decimal("0.04"),
        )
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_confidence_score_above_maximum_raises(self, test_db_session):
        """Check constraint: confidence_score <= 1.00."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            confidence_score=Decimal("1.01"),
        )
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_confidence_score_zero_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            confidence_score=Decimal("0.00"),
        )
        test_db_session.add(snapshot)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()


# ===========================================================================
# QueueSnapshot — Campos opcionais e flags
# ===========================================================================


class TestQueueSnapshotOptionalFields:
    async def test_override_active_defaults_to_false(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        assert snapshot.override_active is False

    async def test_override_active_stores_true(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            override_active=True,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.override_active is True

    async def test_last_report_at_is_nullable(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            last_report_at=None,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.last_report_at is None

    async def test_last_report_at_stores_datetime(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        now = datetime.now(tz=timezone.utc)

        snapshot = QueueSnapshotDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
            last_report_at=now,
        )
        await persist(test_db_session, snapshot)

        assert snapshot.last_report_at is not None


# ===========================================================================
# QueueSnapshot — Relacionamento e integridade referencial
# ===========================================================================


class TestQueueSnapshotRelationships:
    async def test_cascade_delete_removes_snapshot(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        snapshot = QueueSnapshotDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, snapshot)

        ru_id = snapshot.ru_id
        meal_period = snapshot.meal_period

        await test_db_session.delete(restaurant)
        await test_db_session.flush()

        result = await test_db_session.get(
            QueueSnapshot,
            {"ru_id": ru_id, "meal_period": meal_period},
        )
        assert result is None

    async def test_snapshots_from_different_restaurants_same_period(
        self, test_db_session
    ):
        """Dois restaurants diferentes podem ter snapshot no mesmo período."""
        r1 = RestaurantPalmaresDBFactory()
        r2 = RestaurantAurorasDBFactory()
        await persist(test_db_session, r1, r2)

        s1 = QueueSnapshotDBFactory(
            ru_id=r1.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        s2 = QueueSnapshotDBFactory(
            ru_id=r2.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, s1, s2)

        assert s1.ru_id != s2.ru_id
        assert s1.meal_period == s2.meal_period
