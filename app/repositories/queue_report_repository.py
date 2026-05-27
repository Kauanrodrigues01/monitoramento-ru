from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_reports import QueueReport
from app.models.restaurant import MealPeriodEnum


class QueueReportRepository:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def create(self, queue_report: QueueReport) -> QueueReport:
        self.db_session.add(queue_report)
        await self.db_session.flush()
        await self.db_session.refresh(queue_report)
        return queue_report

    async def get_last_by_ip_hash_within_minutes(
        self, ip_hash: str, minutes: int
    ) -> QueueReport | None:
        cutoff = datetime.now() - timedelta(minutes=minutes)
        result = await self.db_session.execute(
            select(QueueReport)
            .where(QueueReport.ip_hash == ip_hash, QueueReport.created_at >= cutoff)
            .order_by(QueueReport.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_recent_by_period(
        self,
        ru_id: int,
        meal_period: MealPeriodEnum,
        day: date,
        limit: int = 100,
        offset: int = 0,
    ) -> list[QueueReport]:
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        query = (
            select(QueueReport)
            .where(
                QueueReport.ru_id == ru_id,
                QueueReport.meal_period == meal_period,
                QueueReport.created_at >= day_start,
                QueueReport.created_at < day_end,
            )
            .order_by(QueueReport.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db_session.execute(query)
        return result.scalars().all()

    async def list_recent_by_period_within_minutes(
        self,
        ru_id: int,
        meal_period: MealPeriodEnum,
        minutes: int,
    ) -> list[QueueReport]:
        cutoff = datetime.now() - timedelta(minutes=minutes)
        result = await self.db_session.execute(
            select(QueueReport)
            .where(
                QueueReport.ru_id == ru_id,
                QueueReport.meal_period == meal_period,
                QueueReport.created_at >= cutoff,
            )
            .order_by(QueueReport.created_at.desc())
        )
        return result.scalars().all()
