"""Seed de desenvolvimento — cria relatos variados para todos os restaurantes.

Uso:
    python -m app.core.seed_dev

Pré-requisito: seed.py já ter sido executado (restaurantes + snapshots devem existir).
Os relatos são criados com created_at retroativos (UTC) para simular uso real.
O snapshot de cada restaurante é recalculado ao final via SnapshotStatusService.
"""

import asyncio
import hashlib
import random
from datetime import timedelta
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.datetime_utils import to_app_tz, utc_now
from app.models.queue_reports import QueueReport, ReportStatusEnum
from app.models.queue_snapshot import QueueSnapshot
from app.models.restaurant import MealPeriodEnum, Restaurant
from app.services.ip_service import IpService

# ── configuração ──────────────────────────────────────────────────────────────

# Quantos relatos criar por restaurante por período
REPORTS_PER_RU_PER_PERIOD = 8

# Distribuição de status (peso relativo)
STATUS_WEIGHTS = {
    ReportStatusEnum.NO_QUEUE: 1,
    ReportStatusEnum.SMALL: 3,
    ReportStatusEnum.MEDIUM: 3,
    ReportStatusEnum.LARGE: 2,
    ReportStatusEnum.FOOD_ENDED: 1,
}

# IPs fictícios para simular usuários distintos
_FAKE_IPS = [f"10.0.0.{i}" for i in range(1, 30)]


def _weighted_status() -> ReportStatusEnum:
    statuses = list(STATUS_WEIGHTS.keys())
    weights = list(STATUS_WEIGHTS.values())
    return random.choices(statuses, weights=weights, k=1)[0]


def _fake_ip_hash() -> str:
    ip = random.choice(_FAKE_IPS)
    return IpService.hash_ip(ip)


def _fake_device_hash() -> str:
    device_id = str(uuid4())
    device_hash = hashlib.sha256(device_id.encode()).hexdigest()
    return device_hash


def _near_coords(lat: float, lng: float, radius_m: int) -> tuple[Decimal, Decimal]:
    """Gera coordenadas dentro do raio do restaurante."""
    # ~1m ≈ 0.000009 graus; deixamos dentro do raio com margem
    delta = (radius_m * 0.000009) * random.uniform(0.0, 0.85)
    angle = random.uniform(0, 360)
    import math

    dlat = delta * math.cos(math.radians(angle))
    dlng = delta * math.sin(math.radians(angle))
    return Decimal(str(round(lat + dlat, 6))), Decimal(str(round(lng + dlng, 6)))


async def seed_reports() -> None:
    async with AsyncSessionLocal() as session:
        now_utc = utc_now()
        now_local = to_app_tz(now_utc)

        restaurants = (
            (
                await session.execute(
                    select(Restaurant).where(Restaurant.is_active == True)  # noqa: E712
                )
            )
            .scalars()
            .all()
        )

        if not restaurants:
            print("Nenhum restaurante encontrado. Execute seed.py primeiro.")
            return

        reports_created = 0
        snapshots_updated = 0

        for restaurant in restaurants:
            ru_lat = float(restaurant.lat)
            ru_lng = float(restaurant.lng)

            for meal_period in (MealPeriodEnum.LUNCH, MealPeriodEnum.DINNER):
                for i in range(REPORTS_PER_RU_PER_PERIOD):
                    # Espalha os relatos nos últimos 14 minutos
                    seconds_ago = random.uniform(30, 14 * 60)
                    created_at = now_utc - timedelta(seconds=seconds_ago)

                    status = _weighted_status()
                    lat, lng = _near_coords(
                        ru_lat, ru_lng, restaurant.geofence_radius_m
                    )
                    accuracy_m = Decimal(str(round(random.uniform(5.0, 30.0), 2)))
                    confidence_score = Decimal(
                        str(round(random.uniform(0.70, 1.00), 2))
                    )

                    report = QueueReport(
                        public_id=uuid4(),
                        ru_id=restaurant.id,
                        meal_period=meal_period,
                        status=status,
                        lat=lat,
                        lng=lng,
                        ip_hash=_fake_ip_hash(),
                        device_hash=_fake_device_hash(),
                        accuracy_m=accuracy_m,
                        confidence_score=confidence_score,
                        is_mock_location=False,
                    )
                    # Sobrescreve created_at depois do flush para contornar server_default
                    session.add(report)
                    await session.flush()
                    report.created_at = created_at
                    reports_created += 1

            print(
                f"  {restaurant.name}: {REPORTS_PER_RU_PER_PERIOD * 2} relatos criados "
                f"(LUNCH + DINNER)"
            )

        await session.commit()

        # Recalcula snapshot de cada RU com base nos relatos recém-criados
        for restaurant in restaurants:
            for meal_period in (MealPeriodEnum.LUNCH, MealPeriodEnum.DINNER):
                snapshot = await session.scalar(
                    select(QueueSnapshot).where(
                        QueueSnapshot.ru_id == restaurant.id,
                        QueueSnapshot.meal_period == meal_period,
                    )
                )
                if not snapshot:
                    continue

                # Busca relatos dos últimos 15min desse período
                cutoff = now_utc - timedelta(minutes=15)
                recent = (
                    (
                        await session.execute(
                            select(QueueReport)
                            .where(
                                QueueReport.ru_id == restaurant.id,
                                QueueReport.meal_period == meal_period,
                                QueueReport.created_at >= cutoff,
                            )
                            .order_by(QueueReport.created_at.desc())
                        )
                    )
                    .scalars()
                    .all()
                )

                if not recent:
                    continue

                # Calcula status simples: média ponderada por confidence
                from app.services.snapshot_status_service import (
                    SnapshotStatusService,
                )

                # Reutiliza a lógica pura _compute_status sem instanciar o serviço completo
                # (evita deps de repos que não precisamos aqui)
                svc_stub = object.__new__(SnapshotStatusService)
                new_status, new_confidence, _ = svc_stub._compute_status(recent)  # type: ignore[attr-defined]

                snapshot.current_status = new_status
                snapshot.reports_last_15m = len(recent)
                snapshot.last_report_at = recent[0].created_at
                snapshot.confidence_score = new_confidence
                snapshots_updated += 1

        await session.commit()

        print(
            f"\nSeed dev concluído: {reports_created} relato(s) criado(s), "
            f"{snapshots_updated} snapshot(s) recalculado(s)."
        )
        print(
            f"Horário local de referência: {now_local.strftime('%Y-%m-%d %H:%M:%S %Z')}"
        )


if __name__ == "__main__":
    asyncio.run(seed_reports())
