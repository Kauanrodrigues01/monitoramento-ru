from datetime import datetime
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.exceptions.geo_signature_exceptions import (
    ExpiredGeoSignatureException,
    InvalidGeoSignatureException,
)
from app.exceptions.meal_period_exceptions import (
    MealPeriodClosedError,
    OutsideMealHoursError,
    RestaurantClosedAllDayError,
)
from app.exceptions.queue_report_exceptions import (
    QueueReportLocationOutOfGeofenceError,
    QueueReportTooRecentError,
)
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_reports import QueueReport
from app.models.restaurant import MealPeriodEnum
from app.tests.unit.services.queue_report_service._base import (
    _GEO_TIMESTAMP,
    _IP,
    _IP_HASH,
    _PATCH_CONFIDENCE,
    _PATCH_GEO_SIG,
    _PATCH_HAVERSINE,
    _PATCH_SETTINGS,
    _UNKNOWN_IP_HASH,
    _make_queue_report,
    _setup_full_happy_path,
)

# ── TestCreateQueueReport_HappyPath ───────────────────────────────────────────


class TestCreateQueueReport_HappyPath:
    async def test_report_created_successfully_returns_queue_report(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        queue_report = _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP
            )

        assert result is queue_report

    async def test_report_created_with_ip_hash_of_received_ip(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.ip_hash == _IP_HASH

    async def test_meal_period_inferred_from_geo_timestamp_not_now(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        expected_at = datetime.fromtimestamp(_GEO_TIMESTAMP)
        mock_meal_period_service.resolve.assert_called_once_with(
            ru_id=restaurant.id,
            at=expected_at,
        )

    async def test_schema_only_fields_excluded_from_model(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        created: QueueReport = mock_repo.create.call_args[0][0]
        instance_keys = {k for k in vars(created) if not k.startswith("_")}
        assert "geo_signature" not in instance_keys
        assert "geo_timestamp" not in instance_keys

    async def test_meal_period_from_service_is_saved_on_report(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo,
            mock_restaurant_repo,
            mock_meal_period_service,
            restaurant,
            meal_period=MealPeriodEnum.DINNER,
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.meal_period == MealPeriodEnum.DINNER


# ── TestCreateQueueReport_Restaurant ─────────────────────────────────────────


class TestCreateQueueReport_Restaurant:
    async def test_restaurant_not_found_raises_restaurant_not_found_error(
        self, service, mock_restaurant_repo, valid_payload
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.create_queue_report(uuid4(), valid_payload, _IP)

    async def test_restaurant_found_continues_pipeline(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        queue_report = _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP
            )

        assert result is queue_report

    async def test_restaurant_looked_up_by_correct_public_id(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_restaurant_repo.get_by_public_id.assert_called_once_with(
            restaurant.public_id
        )


# ── TestCreateQueueReport_GeoSignature ───────────────────────────────────────


class TestCreateQueueReport_GeoSignature:
    async def test_invalid_signature_raises_invalid_geo_signature(
        self, service, mock_restaurant_repo, restaurant, valid_payload
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with (
            patch(_PATCH_GEO_SIG, side_effect=InvalidGeoSignatureException()),
        ):
            with pytest.raises(InvalidGeoSignatureException):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_expired_signature_raises_expired_geo_signature(
        self, service, mock_restaurant_repo, restaurant, valid_payload
    ):
        """
        Signature is expired when abs(now - geo_timestamp) > GEO_SIGNATURE_MAX_SKEW_SECONDS
        (default 60s; 86400s with DEBUG=True). Simulate with geo_timestamp = int(time.time()) - 61.
        """
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with (
            patch(_PATCH_GEO_SIG, side_effect=ExpiredGeoSignatureException()),
        ):
            with pytest.raises(ExpiredGeoSignatureException):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_invalid_signature_does_not_check_cooldown(
        self, service, mock_repo, mock_restaurant_repo, restaurant, valid_payload
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with (
            patch(_PATCH_GEO_SIG, side_effect=InvalidGeoSignatureException()),
        ):
            with pytest.raises(InvalidGeoSignatureException):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

        mock_repo.get_last_by_ip_hash_within_minutes.assert_not_called()

    async def test_geo_signature_validated_with_correct_payload_fields(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG) as mock_validate,
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_validate.assert_called_once_with(
            lat=valid_payload.lat,
            lng=valid_payload.lng,
            accuracy_m=valid_payload.accuracy_m,
            geo_timestamp=valid_payload.geo_timestamp,
            received_signature=valid_payload.geo_signature,
        )


# ── TestCreateQueueReport_Cooldown ────────────────────────────────────────────


class TestCreateQueueReport_Cooldown:
    async def test_ip_none_skips_cooldown_check(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(
                restaurant.public_id, valid_payload, ip=None
            )

        mock_repo.get_last_by_ip_hash_within_minutes.assert_not_called()

    async def test_ip_unknown_string_skips_cooldown_check(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(
                restaurant.public_id, valid_payload, ip="unknown"
            )

        mock_repo.get_last_by_ip_hash_within_minutes.assert_not_called()

    async def test_valid_ip_checks_cooldown_in_repo(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
            patch(_PATCH_SETTINGS) as mock_settings,
        ):
            mock_settings.QUEUE_REPORT_COOLDOWN_MINUTES = 2
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_repo.get_last_by_ip_hash_within_minutes.assert_called_once_with(
            ip_hash=_IP_HASH,
            minutes=2,
        )

    async def test_recent_report_found_raises_queue_report_too_recent_error(
        self, service, mock_repo, mock_restaurant_repo, restaurant, valid_payload
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = _make_queue_report()

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_SETTINGS),
        ):
            with pytest.raises(QueueReportTooRecentError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_no_recent_report_cooldown_passes(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = None

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP
            )

        assert result is not None

    async def test_unknown_ip_stores_hash_of_unknown_not_real_ip(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(
                restaurant.public_id, valid_payload, ip=None
            )

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.ip_hash == _UNKNOWN_IP_HASH

    async def test_active_cooldown_does_not_resolve_meal_period(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = _make_queue_report()

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_SETTINGS),
        ):
            with pytest.raises(QueueReportTooRecentError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

        mock_meal_period_service.resolve.assert_not_called()


# ── TestCreateQueueReport_MealPeriod ─────────────────────────────────────────


class TestCreateQueueReport_MealPeriod:
    async def test_restaurant_closed_all_day_raises_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(RestaurantClosedAllDayError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_outside_operating_hours_raises_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(OutsideMealHoursError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_specific_period_closed_raises_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(MealPeriodClosedError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_meal_period_resolved_with_restaurant_ru_id(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_meal_period_service.resolve.assert_called_once_with(
            ru_id=restaurant.id,
            at=datetime.fromtimestamp(_GEO_TIMESTAMP),
        )

    async def test_invalid_hours_does_not_check_geofence(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_ip_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE) as mock_haversine,
            patch(_PATCH_CONFIDENCE),
        ):
            with pytest.raises(OutsideMealHoursError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

        mock_haversine.assert_not_called()


# ── TestCreateQueueReport_Geofence ───────────────────────────────────────────


class TestCreateQueueReport_Geofence:
    async def test_location_inside_geofence_passes(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(
                _PATCH_HAVERSINE, return_value=float(restaurant.geofence_radius_m) - 1
            ),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP
            )

        assert result is not None

    async def test_location_exactly_at_boundary_passes(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=float(restaurant.geofence_radius_m)),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP
            )

        assert result is not None

    async def test_location_outside_geofence_raises_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(
                _PATCH_HAVERSINE, return_value=float(restaurant.geofence_radius_m) + 1
            ),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            with pytest.raises(QueueReportLocationOutOfGeofenceError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

    async def test_geofence_calculated_with_payload_and_restaurant_coords(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0) as mock_haversine,
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_haversine.assert_called_once_with(
            lat1=float(valid_payload.lat),
            lng1=float(valid_payload.lng),
            lat2=float(restaurant.lat),
            lng2=float(restaurant.lng),
        )


# ── TestCreateQueueReport_ConfidenceScore ────────────────────────────────────


class TestCreateQueueReport_ConfidenceScore:
    async def test_confidence_score_calculated_and_saved_on_report(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )
        expected_score = Decimal("0.75")

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=expected_score),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.confidence_score == expected_score

    async def test_confidence_score_receives_correct_payload_fields(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")) as mock_confidence,
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_confidence.assert_called_once_with(
            lat=valid_payload.lat,
            lng=valid_payload.lng,
            is_mock_location=valid_payload.is_mock_location,
            accuracy_m=valid_payload.accuracy_m,
        )

    async def test_confidence_score_calculated_before_geofence(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        """When outside geofence, the score is already calculated but the report is not persisted."""
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(
                _PATCH_HAVERSINE, return_value=float(restaurant.geofence_radius_m) + 1
            ),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("0.50")) as mock_confidence,
        ):
            with pytest.raises(QueueReportLocationOutOfGeofenceError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

        mock_confidence.assert_called_once()
        mock_repo.create.assert_not_called()


# ── TestCreateQueueReport_Persistence ────────────────────────────────────────


class TestCreateQueueReport_Persistence:
    async def test_repo_create_and_commit_called_on_success(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_repo.create.assert_called_once()
        mock_repo.db_session.commit.assert_called_once()

    async def test_exception_in_create_triggers_rollback_and_reraises(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )
        mock_repo.create.side_effect = RuntimeError("db error")

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            with pytest.raises(RuntimeError, match="db error"):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

        mock_repo.db_session.rollback.assert_called_once()

    async def test_exception_in_commit_triggers_rollback_and_reraises(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )
        mock_repo.db_session.commit.side_effect = RuntimeError("commit error")

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            with pytest.raises(RuntimeError, match="commit error"):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP
                )

        mock_repo.db_session.rollback.assert_called_once()

    async def test_rollback_not_called_on_success(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(restaurant.public_id, valid_payload, _IP)

        mock_repo.db_session.rollback.assert_not_called()
