from decimal import Decimal


from app.core.geo_utils import GeoUtils


class TestHaversineDistanceM:
    def test_same_point_returns_zero(self):
        distance = GeoUtils.haversine_distance_m(0.0, 0.0, 0.0, 0.0)

        assert distance == 0.0

    def test_one_degree_longitude_on_equator(self):
        # 1 grau de longitude no equador ≈ 111.195 km
        distance = GeoUtils.haversine_distance_m(0.0, 0.0, 0.0, 1.0)

        assert abs(distance - 111_195) < 100

    def test_one_degree_latitude(self):
        # 1 grau de latitude ≈ 111.195 km (constante ao longo do meridiano)
        distance = GeoUtils.haversine_distance_m(0.0, 0.0, 1.0, 0.0)

        assert abs(distance - 111_195) < 100

    def test_distance_is_symmetric(self):
        lat1, lng1 = -3.747360, -38.523060
        lat2, lng2 = -3.749000, -38.521000

        d_ab = GeoUtils.haversine_distance_m(lat1, lng1, lat2, lng2)
        d_ba = GeoUtils.haversine_distance_m(lat2, lng2, lat1, lng1)

        assert abs(d_ab - d_ba) < 1e-6

    def test_distance_is_always_non_negative(self):
        distance = GeoUtils.haversine_distance_m(-90.0, -180.0, 90.0, 180.0)

        assert distance >= 0

    def test_antipodal_points_are_half_earth_circumference(self):
        # Pontos antipodais: distância ≈ metade da circunferência terrestre (≈ 20.015 km)
        distance = GeoUtils.haversine_distance_m(0.0, 0.0, 0.0, 180.0)

        assert abs(distance - 20_015_087) < 1000

    def test_small_distance_within_campus(self):
        # Dois pontos separados por ~200 metros dentro do mesmo campus
        lat1, lng1 = -3.747360, -38.523060
        lat2, lng2 = -3.748800, -38.523060

        distance = GeoUtils.haversine_distance_m(lat1, lng1, lat2, lng2)

        assert 155 < distance < 165

    def test_poles(self):
        # Do polo norte ao polo sul: ≈ 20.015 km
        distance = GeoUtils.haversine_distance_m(90.0, 0.0, -90.0, 0.0)

        assert abs(distance - 20_015_087) < 1000

    def test_returns_float(self):
        distance = GeoUtils.haversine_distance_m(1.0, 1.0, 2.0, 2.0)

        assert isinstance(distance, float)

    def test_negative_coordinates_work_correctly(self):
        distance = GeoUtils.haversine_distance_m(
            -3.747360, -38.523060, -3.747360, -38.523060
        )

        assert distance == 0.0


class TestHasSuspiciousRoundCoordinates:
    def test_lat_ends_with_three_zeros_is_suspicious(self):
        # "-4.123000" termina em "000"
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-4.123000"), lng=Decimal("-38.523456")
        )

        assert result is True

    def test_lng_ends_with_three_zeros_is_suspicious(self):
        # "-38.450000" termina em "0000"
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-3.747360"), lng=Decimal("-38.450000")
        )

        assert result is True

    def test_lat_ends_with_four_zeros_is_suspicious(self):
        # "-3.120000" termina em "0000"
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-3.120000"), lng=Decimal("-38.523456")
        )

        assert result is True

    def test_both_suspicious_returns_true(self):
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-4.000000"), lng=Decimal("-38.000000")
        )

        assert result is True

    def test_neither_suspicious_returns_false(self):
        # 2 zeros no final não basta para ser suspeito
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-3.747360"), lng=Decimal("-38.523456")
        )

        assert result is False

    def test_two_trailing_zeros_not_suspicious(self):
        # "-3.123400" termina em "00", não "000"
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-3.1234"), lng=Decimal("-38.5678")
        )

        assert result is False

    def test_one_trailing_zero_not_suspicious(self):
        # "-3.123450" termina em "0", não "000"
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-3.12345"), lng=Decimal("-38.12345")
        )

        assert result is False

    def test_no_trailing_zero_not_suspicious(self):
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("-3.747360"), lng=Decimal("-38.523061")
        )

        assert result is False

    def test_positive_coordinates_also_detected(self):
        # Coordenadas positivas com arredondamento suspeito
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("4.123000"), lng=Decimal("38.523456")
        )

        assert result is True

    def test_zero_coordinates_are_suspicious(self):
        # 0.000000 termina em "0000"
        result = GeoUtils.has_suspicious_round_coordinates(
            lat=Decimal("0"), lng=Decimal("0")
        )

        assert result is True
