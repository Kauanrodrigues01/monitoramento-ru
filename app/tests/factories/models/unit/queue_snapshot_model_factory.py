from datetime import UTC, datetime

import factory
from app.tests.factories.models.base.queue_snapshot_base_model_factory import (
    BaseQueueSnapshotFactory,
)


class QueueSnapshotFactory(BaseQueueSnapshotFactory):
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))
