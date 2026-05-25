from app.models.queue_reports import ReportStatusEnum
from app.schemas.queue_report_schemas import QueueReportCreate

_VALID_geo_signature = "a" * 64


def build_queue_report_create_schema(**kwargs) -> QueueReportCreate:
    data: dict = {
        "status": ReportStatusEnum.SMALL,
        "lat": "-3.747361",
        "lng": "-38.523060",
        "geo_signature": _VALID_geo_signature,
        "geo_timestamp": 1748166600,
    }
    data.update(kwargs)
    return QueueReportCreate(**data)
