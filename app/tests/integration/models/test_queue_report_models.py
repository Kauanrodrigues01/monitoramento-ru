from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.queue_reports import QueueReport, ReportStatusEnum
from app.models.restaurant import MealPeriodEnum
from app.tests.factories.models.integration.queue_report_model_factory import (
    QueueReportDBFactory,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantAurorasDBFactory,
    RestaurantPalmaresDBFactory,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _persist(session, *instances):
    for instance in instances:
        session.add(instance)
    await session.flush()
    for instance in instances:
        await session.refresh(instance)
    return instances if len(instances) > 1 else instances[0]


# ===========================================================================
# QueueReport — Criação e campos básicos
# ===========================================================================


class TestQueueReportCreation:
    async def test_creates_with_required_fields(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        assert report.id is not None

    async def test_generates_integer_primary_key(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        assert isinstance(report.id, int)
        assert report.id > 0

    async def test_generates_uuid_public_id(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        assert isinstance(report.public_id, UUID)

    async def test_public_id_is_unique_across_reports(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        r1 = QueueReportDBFactory(ru_id=restaurant.id)
        r2 = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, r1, r2)

        # public_id gerado em Python antes do flush
        assert r1.public_id != r2.public_id

    async def test_public_id_unique_constraint_is_enforced(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        r1 = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, r1)

        r2 = QueueReportDBFactory(ru_id=restaurant.id, public_id=r1.public_id)
        test_db_session.add(r2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_created_at_is_set_automatically(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        assert report.created_at is not None

    async def test_stores_lat_lng_as_decimal(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            lat=Decimal("-4.215432"),
            lng=Decimal("-38.727981"),
        )
        await _persist(test_db_session, report)

        assert isinstance(report.lat, Decimal)
        assert isinstance(report.lng, Decimal)


# ===========================================================================
# QueueReport — Campos de status e período
# ===========================================================================


class TestQueueReportStatusAndPeriod:
    async def test_stores_status_no_queue(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            status=ReportStatusEnum.NO_QUEUE,
        )
        await _persist(test_db_session, report)

        assert report.status == ReportStatusEnum.NO_QUEUE

    async def test_stores_status_small(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            status=ReportStatusEnum.SMALL,
        )
        await _persist(test_db_session, report)

        assert report.status == ReportStatusEnum.SMALL

    async def test_stores_status_medium(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            status=ReportStatusEnum.MEDIUM,
        )
        await _persist(test_db_session, report)

        assert report.status == ReportStatusEnum.MEDIUM

    async def test_stores_status_large(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            status=ReportStatusEnum.LARGE,
        )
        await _persist(test_db_session, report)

        assert report.status == ReportStatusEnum.LARGE

    async def test_stores_status_food_ended(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            status=ReportStatusEnum.FOOD_ENDED,
        )
        await _persist(test_db_session, report)

        assert report.status == ReportStatusEnum.FOOD_ENDED

    async def test_stores_meal_period_lunch(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await _persist(test_db_session, report)

        assert report.meal_period == MealPeriodEnum.LUNCH

    async def test_stores_meal_period_dinner(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
        )
        await _persist(test_db_session, report)

        assert report.meal_period == MealPeriodEnum.DINNER


# ===========================================================================
# QueueReport — Campos de privacidade (hashes)
# ===========================================================================


class TestQueueReportPrivacyFields:
    async def test_ip_hash_stored_with_64_chars(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        ip_hash = "a" * 64
        report = QueueReportDBFactory(ru_id=restaurant.id, ip_hash=ip_hash)
        await _persist(test_db_session, report)

        assert report.ip_hash == ip_hash
        assert len(report.ip_hash) == 64

    async def test_device_hash_stored_with_64_chars(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        device_hash = "b" * 64
        report = QueueReportDBFactory(ru_id=restaurant.id, device_hash=device_hash)
        await _persist(test_db_session, report)

        assert report.device_hash == device_hash
        assert len(report.device_hash) == 64

    async def test_different_reports_can_share_same_ip_hash(self, test_db_session):
        """Não há unique constraint em ip_hash — múltiplos reports do mesmo IP são permitidos."""
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        shared_ip_hash = "c" * 64

        r1 = QueueReportDBFactory(ru_id=restaurant.id, ip_hash=shared_ip_hash)
        r2 = QueueReportDBFactory(ru_id=restaurant.id, ip_hash=shared_ip_hash)
        await _persist(test_db_session, r1, r2)

        assert r1.id is not None
        assert r2.id is not None

    async def test_different_reports_can_share_same_device_hash(self, test_db_session):
        """Não há unique constraint em device_hash — múltiplos reports do mesmo dispositivo são permitidos."""
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        shared_device_hash = "d" * 64

        r1 = QueueReportDBFactory(ru_id=restaurant.id, device_hash=shared_device_hash)
        r2 = QueueReportDBFactory(ru_id=restaurant.id, device_hash=shared_device_hash)
        await _persist(test_db_session, r1, r2)

        assert r1.id is not None
        assert r2.id is not None


# ===========================================================================
# QueueReport — confidence_score
# ===========================================================================


class TestQueueReportConfidenceScore:
    async def test_default_confidence_score_is_one(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        assert report.confidence_score == Decimal("1.00")

    async def test_stores_minimum_valid_confidence_score(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("0.05"),
        )
        await _persist(test_db_session, report)

        assert report.confidence_score == Decimal("0.05")

    async def test_stores_maximum_valid_confidence_score(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("1.00"),
        )
        await _persist(test_db_session, report)

        assert report.confidence_score == Decimal("1.00")

    async def test_stores_mid_range_confidence_score(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("0.50"),
        )
        await _persist(test_db_session, report)

        assert report.confidence_score == Decimal("0.50")

    async def test_confidence_score_below_minimum_raises(self, test_db_session):
        """Check constraint: confidence_score >= 0.05."""
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("0.04"),
        )
        test_db_session.add(report)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_confidence_score_above_maximum_raises(self, test_db_session):
        """Check constraint: confidence_score <= 1.00."""
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("1.01"),
        )
        test_db_session.add(report)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_confidence_score_zero_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            confidence_score=Decimal("0.00"),
        )
        test_db_session.add(report)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()


# ===========================================================================
# QueueReport — Campos opcionais
# ===========================================================================


class TestQueueReportOptionalFields:
    async def test_accuracy_m_is_nullable(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id, accuracy_m=None)
        await _persist(test_db_session, report)

        assert report.accuracy_m is None

    async def test_accuracy_m_stores_value(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            accuracy_m=Decimal("12.50"),
        )
        await _persist(test_db_session, report)

        assert report.accuracy_m == Decimal("12.50")

    async def test_is_mock_location_defaults_to_false(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        assert report.is_mock_location is False

    async def test_is_mock_location_stores_true(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(
            ru_id=restaurant.id,
            is_mock_location=True,
        )
        await _persist(test_db_session, report)

        assert report.is_mock_location is True


# ===========================================================================
# QueueReport — Relacionamento e integridade referencial
# ===========================================================================


class TestQueueReportRelationships:
    async def test_cascade_delete_removes_reports(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        report = QueueReportDBFactory(ru_id=restaurant.id)
        await _persist(test_db_session, report)

        report_id = report.id

        await test_db_session.delete(restaurant)
        await test_db_session.flush()

        result = await test_db_session.get(QueueReport, report_id)
        assert result is None

    async def test_invalid_ru_id_raises(self, test_db_session):
        """FK constraint: ru_id deve referenciar um restaurant existente."""
        report = QueueReportDBFactory(ru_id=999999)
        test_db_session.add(report)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_multiple_reports_for_same_restaurant(self, test_db_session):
        """Um restaurant pode ter N reports — sem unique constraint em ru_id."""
        restaurant = RestaurantPalmaresDBFactory()
        await _persist(test_db_session, restaurant)

        reports = [QueueReportDBFactory(ru_id=restaurant.id) for _ in range(3)]
        await _persist(test_db_session, *reports)

        assert all(r.id is not None for r in reports)
        assert len({r.id for r in reports}) == 3

    async def test_reports_from_different_restaurants(self, test_db_session):
        r1 = RestaurantPalmaresDBFactory()
        r2 = RestaurantAurorasDBFactory()
        await _persist(test_db_session, r1, r2)

        rep1 = QueueReportDBFactory(ru_id=r1.id)
        rep2 = QueueReportDBFactory(ru_id=r2.id)
        await _persist(test_db_session, rep1, rep2)

        assert rep1.ru_id == r1.id
        assert rep2.ru_id == r2.id
