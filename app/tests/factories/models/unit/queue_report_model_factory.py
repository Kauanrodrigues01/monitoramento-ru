from datetime import UTC, datetime
from uuid import uuid4

import factory

from app.tests.factories.models.base.queue_report_base_model_factory import (
    BaseQueueReportFactory,
)


class QueueReportFactory(BaseQueueReportFactory):
    id = factory.Sequence(lambda n: n + 1)

    public_id = factory.LazyFunction(uuid4)

    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
