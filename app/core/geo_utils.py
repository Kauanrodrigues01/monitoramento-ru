import math
from decimal import Decimal


class GeoUtils:
    @staticmethod
    def haversine_distance_m(
        lat1: float, lng1: float, lat2: float, lng2: float
    ) -> float:
        R = 6_371_000  # raio médio da Terra em metros

        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlambda = math.radians(lng2 - lng1)

        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    @staticmethod
    def has_suspicious_round_coordinates(lat: Decimal, lng: Decimal) -> bool:
        """
        Verifica se latitude/longitude parecem excessivamente arredondadas.

        Ex:
        -4.123000 -> suspeito
        -38.450000 -> suspeito
        """
        lat_str = f"{lat:.6f}"
        lng_str = f"{lng:.6f}"

        return lat_str.endswith(("000", "0000")) or lng_str.endswith(("000", "0000"))
