from datetime import date, time
from decimal import Decimal
from uuid import UUID

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.restaurant import (
    CampusEnum,
    ExceptionTypeEnum,
    MealPeriodEnum,
    RestaurantSchedule,
    RestaurantScheduleException,
)
from app.tests.factories.models.integration.restaurant_model_factory import (
    RestaurantAurorasDBFactory,
    RestaurantDBFactory,
    RestaurantLiberdadeDBFactory,
    RestaurantPalmaresDBFactory,
    RestaurantScheduleDBFactory,
    RestaurantScheduleExceptionDBFactory,
)
from app.tests.integration.helpers import persist

pytestmark = pytest.mark.asyncio(loop_scope="session")

# ===========================================================================
# Restaurant
# ===========================================================================


class TestRestaurantCreation:
    async def test_creates_with_required_fields(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.id is not None

    async def test_generates_integer_primary_key(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert isinstance(restaurant.id, int)
        assert restaurant.id > 0

    async def test_generates_uuid_public_id(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert isinstance(restaurant.public_id, UUID)

    async def test_public_id_is_unique_across_restaurants(self, test_db_session):
        r1 = RestaurantDBFactory()
        r2 = RestaurantDBFactory()
        await persist(test_db_session, r1, r2)

        assert r1.public_id != r2.public_id

    async def test_public_id_unique_constraint_is_enforced(self, test_db_session):
        r1 = RestaurantDBFactory()
        await persist(test_db_session, r1)

        # força o mesmo public_id para disparar o unique constraint
        r2 = RestaurantDBFactory(public_id=r1.public_id)
        test_db_session.add(r2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_name_unique_constraint_is_enforced(self, test_db_session):
        r1 = RestaurantDBFactory(name="RU Único")
        await persist(test_db_session, r1)

        r2 = RestaurantDBFactory(name="RU Único")
        test_db_session.add(r2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_campus_unique_constraint_is_enforced(self, test_db_session):
        r1 = RestaurantAurorasDBFactory()
        await persist(test_db_session, r1)

        r2 = RestaurantAurorasDBFactory(name="RU Auroras 2")
        test_db_session.add(r2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_stores_lat_lng_as_decimal(self, test_db_session):
        restaurant = RestaurantDBFactory(
            lat=Decimal("-4.215432"),
            lng=Decimal("-38.727981"),
        )
        await persist(test_db_session, restaurant)

        assert isinstance(restaurant.lat, Decimal)
        assert isinstance(restaurant.lng, Decimal)

    async def test_geofence_radius_defaults_to_80(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.geofence_radius_m == 80

    async def test_is_active_defaults_to_true(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.is_active is True

    async def test_created_at_is_set_automatically(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.created_at is not None

    async def test_updated_at_is_set_automatically(self, test_db_session):
        restaurant = RestaurantDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.updated_at is not None

    async def test_name_fieldpersists_correctly(self, test_db_session):
        restaurant = RestaurantDBFactory(name="RU Campo Alegre")
        await persist(test_db_session, restaurant)

        assert restaurant.name == "RU Campo Alegre"


class TestRestaurantCampusVariants:
    async def test_creates_palmares_campus(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.campus == CampusEnum.PALMARES

    async def test_creates_auroras_campus(self, test_db_session):
        restaurant = RestaurantAurorasDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.campus == CampusEnum.AURORAS

    async def test_creates_liberdade_campus(self, test_db_session):
        restaurant = RestaurantLiberdadeDBFactory()
        await persist(test_db_session, restaurant)

        assert restaurant.campus == CampusEnum.LIBERDADE


# ===========================================================================
# RestaurantSchedule
# ===========================================================================


class TestRestaurantScheduleCreation:
    async def test_creates_with_valid_data(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, schedule)

        assert schedule.id is not None

    async def test_generates_uuid_public_id(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, schedule)

        assert isinstance(schedule.public_id, UUID)

    async def test_meal_period_stored_correctly(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            meal_period=MealPeriodEnum.DINNER,
        )
        await persist(test_db_session, schedule)

        assert schedule.meal_period == MealPeriodEnum.DINNER

    async def test_opens_and_closes_at_stored_correctly(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            opens_at=time(11, 0),
            closes_at=time(14, 0),
        )
        await persist(test_db_session, schedule)

        assert schedule.opens_at == time(11, 0)
        assert schedule.closes_at == time(14, 0)

    async def test_is_active_defaults_to_true(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, schedule)

        assert schedule.is_active is True


class TestRestaurantScheduleConstraints:
    async def test_weekday_below_zero_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(ru_id=restaurant.id, weekday=-1)
        test_db_session.add(schedule)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_weekday_above_five_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(ru_id=restaurant.id, weekday=6)
        test_db_session.add(schedule)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_weekday_boundary_zero_is_valid(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=0,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, schedule)

        assert schedule.id is not None

    async def test_weekday_boundary_five_is_valid(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=5,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, schedule)

        assert schedule.id is not None

    async def test_duplicate_ru_weekday_meal_period_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        s1 = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=1,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, s1)

        s2 = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=1,
            meal_period=MealPeriodEnum.LUNCH,
        )
        test_db_session.add(s2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_same_weekday_different_meal_period_is_allowed(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        lunch = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=2,
            meal_period=MealPeriodEnum.LUNCH,
        )
        dinner = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=2,
            meal_period=MealPeriodEnum.DINNER,
        )
        await persist(test_db_session, lunch, dinner)

        assert lunch.id is not None
        assert dinner.id is not None

    async def test_opens_at_after_closes_at_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=3,
            opens_at=time(14, 0),
            closes_at=time(11, 0),  # horário invertido
        )
        test_db_session.add(schedule)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_opens_at_equal_closes_at_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(
            ru_id=restaurant.id,
            weekday=4,
            opens_at=time(11, 0),
            closes_at=time(11, 0),  # igual não satisfaz opens_at < closes_at
        )
        test_db_session.add(schedule)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_cascade_delete_removes_schedules(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        schedule = RestaurantScheduleDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, schedule)

        schedule_id = schedule.id

        await test_db_session.delete(restaurant)
        await test_db_session.flush()

        result = await test_db_session.get(RestaurantSchedule, schedule_id)
        assert result is None


# ===========================================================================
# RestaurantScheduleException
# ===========================================================================


class TestRestaurantScheduleExceptionCreation:
    async def test_creates_closed_whole_day(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_type=ExceptionTypeEnum.CLOSED,
            meal_period=None,
            opens_at=None,
            closes_at=None,
        )
        await persist(test_db_session, exc)

        assert exc.id is not None
        assert exc.meal_period is None
        assert exc.opens_at is None
        assert exc.closes_at is None

    async def test_creates_closed_specific_period(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=date(2025, 6, 15),
            exception_type=ExceptionTypeEnum.CLOSED,
            meal_period=MealPeriodEnum.DINNER,
            opens_at=None,
            closes_at=None,
        )
        await persist(test_db_session, exc)

        assert exc.meal_period == MealPeriodEnum.DINNER

    async def test_creates_custom_hours(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=date(2025, 7, 4),
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            meal_period=MealPeriodEnum.LUNCH,
            opens_at=time(11, 30),
            closes_at=time(13, 0),
        )
        await persist(test_db_session, exc)

        assert exc.exception_type == ExceptionTypeEnum.CUSTOM_HOURS
        assert exc.opens_at == time(11, 30)
        assert exc.closes_at == time(13, 0)

    async def test_reason_field_is_optional(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            reason=None,
        )
        await persist(test_db_session, exc)

        assert exc.reason is None

    async def test_reason_field_stores_value(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=date(2025, 9, 7),
            reason="Feriado Nacional",
        )
        await persist(test_db_session, exc)

        assert exc.reason == "Feriado Nacional"


class TestRestaurantScheduleExceptionConstraints:
    async def test_duplicate_whole_day_exception_raises(self, test_db_session):
        """Índice parcial: uq_restaurant_schedule_exception_whole_day."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        same_date = date(2025, 10, 12)

        e1 = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=same_date,
            meal_period=None,
        )
        await persist(test_db_session, e1)

        e2 = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=same_date,
            meal_period=None,
        )
        test_db_session.add(e2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_duplicate_period_exception_raises(self, test_db_session):
        """UniqueConstraint: (ru_id, exception_date, meal_period)."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        same_date = date(2025, 11, 2)

        e1 = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=same_date,
            meal_period=MealPeriodEnum.LUNCH,
        )
        await persist(test_db_session, e1)

        e2 = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=same_date,
            meal_period=MealPeriodEnum.LUNCH,
        )
        test_db_session.add(e2)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_same_date_different_periods_is_allowed(self, test_db_session):
        """LUNCH e DINNER na mesma data são exceções distintas e válidas."""
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        same_date = date(2025, 8, 20)

        lunch_exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=same_date,
            meal_period=MealPeriodEnum.LUNCH,
        )
        dinner_exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=same_date,
            meal_period=MealPeriodEnum.DINNER,
        )
        await persist(test_db_session, lunch_exc, dinner_exc)

        assert lunch_exc.id is not None
        assert dinner_exc.id is not None

    async def test_different_restaurants_same_date_is_allowed(self, test_db_session):
        """Dois RUs diferentes podem ter exceção no mesmo dia."""
        r1 = RestaurantPalmaresDBFactory()
        r2 = RestaurantAurorasDBFactory()
        await persist(test_db_session, r1, r2)

        same_date = date(2025, 12, 25)

        e1 = RestaurantScheduleExceptionDBFactory(
            ru_id=r1.id,
            exception_date=same_date,
            meal_period=None,
        )
        e2 = RestaurantScheduleExceptionDBFactory(
            ru_id=r2.id,
            exception_date=same_date,
            meal_period=None,
        )
        await persist(test_db_session, e1, e2)

        assert e1.id is not None
        assert e2.id is not None

    async def test_custom_hours_opens_after_closes_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=date(2025, 3, 10),
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            meal_period=MealPeriodEnum.LUNCH,
            opens_at=time(14, 0),
            closes_at=time(11, 0),  # invertido
        )
        test_db_session.add(exc)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_custom_hours_opens_equal_closes_raises(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(
            ru_id=restaurant.id,
            exception_date=date(2025, 4, 1),
            exception_type=ExceptionTypeEnum.CUSTOM_HOURS,
            meal_period=MealPeriodEnum.DINNER,
            opens_at=time(18, 0),
            closes_at=time(18, 0),  # igual, não satisfaz <
        )
        test_db_session.add(exc)

        with pytest.raises(IntegrityError):
            await test_db_session.flush()

        await test_db_session.rollback()

    async def test_cascade_delete_removes_exceptions(self, test_db_session):
        restaurant = RestaurantPalmaresDBFactory()
        await persist(test_db_session, restaurant)

        exc = RestaurantScheduleExceptionDBFactory(ru_id=restaurant.id)
        await persist(test_db_session, exc)

        exc_id = exc.id

        await test_db_session.delete(restaurant)
        await test_db_session.flush()

        result = await test_db_session.get(RestaurantScheduleException, exc_id)
        assert result is None
