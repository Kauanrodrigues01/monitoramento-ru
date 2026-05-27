from app.exceptions.base import AppException


class QueueSnapshotNotFoundError(AppException):
    status_code = 404
    detail = "Snapshot de fila não encontrado para o período informado."


class QueueSnapshotBulkLimitExceededError(AppException):
    status_code = 400
    detail = "O número máximo de RUs por requisição em lote foi excedido."

    def __init__(self) -> None:
        from app.services.queue_snapshot_service import BULK_LIMIT

        super().__init__(
            detail=f"O número máximo de RUs por requisição em lote é {BULK_LIMIT}."
        )
