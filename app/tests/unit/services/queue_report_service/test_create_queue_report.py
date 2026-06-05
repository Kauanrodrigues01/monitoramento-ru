import logging
from datetime import UTC, datetime
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
from app.exceptions.header_exceptions import RequiredDeviceIdHeaderError
from app.exceptions.queue_report_exceptions import (
    QueueReportLocationOutOfGeofenceError,
    QueueReportTooRecentError,
)
from app.exceptions.queue_snapshot_exceptions import QueueSnapshotNotFoundError
from app.exceptions.restaurant_exceptions import RestaurantNotFoundError
from app.models.queue_reports import QueueReport
from app.models.restaurant import MealPeriodEnum
from app.tests.unit.services.queue_report_service._base import (
    _DEVICE_HASH,
    _DEVICE_ID,
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        from app.core.datetime_utils import to_app_tz

        expected_at = to_app_tz(datetime.fromtimestamp(_GEO_TIMESTAMP, tz=UTC))
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

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
        background_tasks,
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
            await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.meal_period == MealPeriodEnum.DINNER


# ── TestCreateQueueReport_Restaurant ─────────────────────────────────────────


class TestCreateQueueReport_Restaurant:
    async def test_restaurant_not_found_raises_restaurant_not_found_error(
        self, service, mock_restaurant_repo, valid_payload, background_tasks
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.create_queue_report(
                uuid4(), valid_payload, _IP, _DEVICE_ID, background_tasks
            )

    async def test_restaurant_found_continues_pipeline(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        mock_restaurant_repo.get_by_public_id.assert_called_once_with(
            restaurant.public_id
        )


# ── TestCreateQueueReport_GeoSignature ───────────────────────────────────────


class TestCreateQueueReport_GeoSignature:
    async def test_invalid_signature_raises_invalid_geo_signature(
        self, service, mock_restaurant_repo, restaurant, valid_payload, background_tasks
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with (
            patch(_PATCH_GEO_SIG, side_effect=InvalidGeoSignatureException()),
        ):
            with pytest.raises(InvalidGeoSignatureException):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_expired_signature_raises_expired_geo_signature(
        self, service, mock_restaurant_repo, restaurant, valid_payload, background_tasks
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
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_invalid_signature_does_not_check_cooldown(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with (
            patch(_PATCH_GEO_SIG, side_effect=InvalidGeoSignatureException()),
        ):
            with pytest.raises(InvalidGeoSignatureException):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

        mock_repo.get_last_by_device_hash_within_minutes.assert_not_called()

    async def test_geo_signature_validated_with_correct_payload_fields(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG) as mock_validate,
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        mock_validate.assert_called_once_with(
            lat=valid_payload.lat,
            lng=valid_payload.lng,
            accuracy_m=valid_payload.accuracy_m,
            geo_timestamp=valid_payload.geo_timestamp,
            received_signature=valid_payload.geo_signature,
        )


# ── TestCreateQueueReport_Cooldown ────────────────────────────────────────────


class TestCreateQueueReport_DeviceId:
    async def test_missing_device_id_raises_required_device_id_header_error(
        self,
        service,
        mock_restaurant_repo,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(RequiredDeviceIdHeaderError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP, None, background_tasks
                )

    async def test_empty_device_id_raises_required_device_id_header_error(
        self,
        service,
        mock_restaurant_repo,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(RequiredDeviceIdHeaderError):
                await service.create_queue_report(
                    restaurant.public_id, valid_payload, _IP, "", background_tasks
                )

    async def test_device_hash_stored_as_sha256_of_device_id(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.device_hash == _DEVICE_HASH


class TestCreateQueueReport_Cooldown:
    async def test_ip_none_does_not_skip_device_cooldown_check(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id,
                valid_payload,
                ip=None,
                device_id=_DEVICE_ID,
                background_tasks=background_tasks,
            )

        mock_repo.get_last_by_device_hash_within_minutes.assert_called_once()

    async def test_ip_unknown_string_does_not_skip_device_cooldown_check(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id,
                valid_payload,
                ip="unknown",
                device_id=_DEVICE_ID,
                background_tasks=background_tasks,
            )

        mock_repo.get_last_by_device_hash_within_minutes.assert_called_once()

    async def test_valid_ip_checks_cooldown_in_repo(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
            await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        mock_repo.get_last_by_device_hash_within_minutes.assert_called_once_with(
            device_hash=_DEVICE_HASH,
            minutes=2,
        )

    async def test_recent_report_found_raises_queue_report_too_recent_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = (
            _make_queue_report()
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_SETTINGS),
        ):
            with pytest.raises(QueueReportTooRecentError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_no_recent_report_cooldown_passes(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )
        mock_repo.get_last_by_device_hash_within_minutes.return_value = None

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
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
        background_tasks,
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
                restaurant.public_id,
                valid_payload,
                ip=None,
                device_id=_DEVICE_ID,
                background_tasks=background_tasks,
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
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = (
            _make_queue_report()
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_SETTINGS),
        ):
            with pytest.raises(QueueReportTooRecentError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
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
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = RestaurantClosedAllDayError()

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(RestaurantClosedAllDayError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_outside_operating_hours_raises_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(OutsideMealHoursError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_specific_period_closed_raises_error(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = MealPeriodClosedError()

        with patch(_PATCH_GEO_SIG):
            with pytest.raises(MealPeriodClosedError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_meal_period_resolved_with_restaurant_ru_id(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        from app.core.datetime_utils import to_app_tz

        mock_meal_period_service.resolve.assert_called_once_with(
            ru_id=restaurant.id,
            at=to_app_tz(datetime.fromtimestamp(_GEO_TIMESTAMP, tz=UTC)),
        )

    async def test_invalid_hours_does_not_calculate_confidence_score(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        """Geofence é validado antes de meal_period; quando meal_period falha,
        confidence_score não chega a ser calculado."""
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = None
        mock_meal_period_service.resolve.side_effect = OutsideMealHoursError()

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE) as mock_confidence,
        ):
            with pytest.raises(OutsideMealHoursError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

        mock_confidence.assert_not_called()


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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
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
        background_tasks,
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
            patch(_PATCH_SETTINGS) as mock_settings,
        ):
            mock_settings.DEBUG = False
            with pytest.raises(QueueReportLocationOutOfGeofenceError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

    async def test_geofence_calculated_with_payload_and_restaurant_coords(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0) as mock_haversine,
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
        ):
            await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        mock_haversine.assert_called_once_with(
            lat1=float(valid_payload.lat),
            lng1=float(valid_payload.lng),
            lat2=float(restaurant.lat),
            lng2=float(restaurant.lng),
        )

    async def test_location_outside_geofence_passes_when_debug_true(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        _setup_full_happy_path(
            mock_repo, mock_restaurant_repo, mock_meal_period_service, restaurant
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(
                _PATCH_HAVERSINE,
                return_value=float(restaurant.geofence_radius_m) + 9999,
            ),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")),
            patch(_PATCH_SETTINGS) as mock_settings,
        ):
            mock_settings.DEBUG = True
            result = await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        assert result is not None
        mock_repo.create.assert_called_once()


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
        background_tasks,
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
            await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        created: QueueReport = mock_repo.create.call_args[0][0]
        assert created.confidence_score == expected_score

    async def test_confidence_score_receives_correct_payload_fields(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        mock_snapshot_repo,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        _setup_full_happy_path(
            mock_repo,
            mock_restaurant_repo,
            mock_meal_period_service,
            restaurant,
            mock_snapshot_repo=mock_snapshot_repo,
        )

        with (
            patch(_PATCH_GEO_SIG),
            patch(_PATCH_HAVERSINE, return_value=50.0),
            patch(_PATCH_CONFIDENCE, return_value=Decimal("1.00")) as mock_confidence,
        ):
            await service.create_queue_report(
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        mock_confidence.assert_called_once_with(
            lat=valid_payload.lat,
            lng=valid_payload.lng,
            is_mock_location=valid_payload.is_mock_location,
            accuracy_m=valid_payload.accuracy_m,
            report_status=valid_payload.status,
            snapshot=mock_snapshot_repo.get_by_ru_id_and_meal_period.return_value,
        )

    async def test_geofence_fails_before_confidence_score_is_calculated(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
    ):
        """Geofence é validado antes de confidence_score; fora do geofence, o score não é calculado."""
        mock_restaurant_repo.get_by_public_id.return_value = restaurant
        mock_repo.get_last_by_device_hash_within_minutes.return_value = None

        with (
            patch(_PATCH_GEO_SIG),
            patch(
                _PATCH_HAVERSINE, return_value=float(restaurant.geofence_radius_m) + 1
            ),
            patch(_PATCH_CONFIDENCE) as mock_confidence,
            patch(_PATCH_SETTINGS) as mock_settings,
        ):
            mock_settings.DEBUG = False
            with pytest.raises(QueueReportLocationOutOfGeofenceError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

        mock_confidence.assert_not_called()
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

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
        background_tasks,
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
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
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
        background_tasks,
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
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
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
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        mock_repo.db_session.rollback.assert_not_called()


# ── TestCreateQueueReport_BackgroundTask ──────────────────────────────────────


class TestCreateQueueReport_BackgroundTask:
    async def test_background_task_registered_after_successful_creation(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        background_tasks.add_task.assert_called_once()

    async def test_background_task_registered_with_correct_handler_and_ru_id(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
                restaurant.public_id, valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        background_tasks.add_task.assert_called_once_with(
            service._update_snapshot_safe, restaurant.id
        )

    async def test_background_task_not_registered_when_restaurant_not_found(
        self,
        service,
        mock_restaurant_repo,
        valid_payload,
        background_tasks,
    ):
        mock_restaurant_repo.get_by_public_id.return_value = None

        with pytest.raises(RestaurantNotFoundError):
            await service.create_queue_report(
                uuid4(), valid_payload, _IP, _DEVICE_ID, background_tasks
            )

        background_tasks.add_task.assert_not_called()

    async def test_background_task_not_registered_when_geofence_violation(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
            patch(_PATCH_SETTINGS) as mock_settings,
        ):
            mock_settings.DEBUG = False
            with pytest.raises(QueueReportLocationOutOfGeofenceError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

        background_tasks.add_task.assert_not_called()

    async def test_background_task_not_registered_on_db_exception(
        self,
        service,
        mock_repo,
        mock_restaurant_repo,
        mock_meal_period_service,
        restaurant,
        valid_payload,
        background_tasks,
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
            with pytest.raises(RuntimeError):
                await service.create_queue_report(
                    restaurant.public_id,
                    valid_payload,
                    _IP,
                    _DEVICE_ID,
                    background_tasks,
                )

        background_tasks.add_task.assert_not_called()


# ── TestUpdateSnapshotSafe ────────────────────────────────────────────────────


class TestUpdateSnapshotSafe:
    async def test_calls_update_snapshot_with_correct_ru_id(
        self, service, mock_snapshot_status_service
    ):
        await service._update_snapshot_safe(ru_id=42)

        mock_snapshot_status_service.update_snapshot.assert_called_once_with(42)

    async def test_swallows_generic_exception(
        self, service, mock_snapshot_status_service
    ):
        mock_snapshot_status_service.update_snapshot.side_effect = RuntimeError("oops")

        await service._update_snapshot_safe(ru_id=1)

    async def test_swallows_queue_snapshot_not_found_error(
        self, service, mock_snapshot_status_service
    ):
        mock_snapshot_status_service.update_snapshot.side_effect = (
            QueueSnapshotNotFoundError()
        )

        await service._update_snapshot_safe(ru_id=1)

    async def test_logs_warning_on_exception(
        self, service, mock_snapshot_status_service, caplog
    ):
        mock_snapshot_status_service.update_snapshot.side_effect = RuntimeError("oops")

        with caplog.at_level(logging.WARNING):
            await service._update_snapshot_safe(ru_id=7)

        assert "Falha ao atualizar snapshot em background" in caplog.text
        assert "7" in caplog.text
