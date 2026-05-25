from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue_reports import QueueReport


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
