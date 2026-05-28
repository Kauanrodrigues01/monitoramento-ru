from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.queue_reports import ReportStatusEnum
from app.models.restaurant import MealPeriodEnum


def truncate_coordinate(value: Decimal) -> Decimal:
    """Trunca lat/lng para 6 casas decimais em direção ao zero (ROUND_DOWN).

    Deve ser chamada APÓS a validação da assinatura geo, pois a truncagem altera
    o valor e tornaria o payload diferente do que o cliente assinou.
    """
    return value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


class QueueReportCreate(BaseModel):
    status: ReportStatusEnum = Field(
        description="Situação atual da fila do restaurante.",
        examples=[ReportStatusEnum.SMALL.value],
    )
    lat: Decimal = Field(
        ge=-90,
        le=90,
        description="Latitude da localização do usuário no momento do relato.",
        examples=[-3.74736],
    )
    lng: Decimal = Field(
        ge=-180,
        le=180,
        description="Longitude da localização do usuário no momento do relato.",
        examples=[-38.52306],
    )
    accuracy_m: Decimal | None = Field(
        default=None,
        ge=0,
        description="Precisão do GPS em metros, conforme reportado pelo dispositivo.",
        examples=[12.5],
    )
    is_mock_location: bool = Field(
        default=False,
        description="Indica se o dispositivo detectou que a localização é simulada (ex: Android isFromMockProvider).",
        examples=[False],
    )
    geo_signature: str = Field(
        min_length=64,
        max_length=64,
        description=(
            "HMAC-SHA256 da assinatura de geolocalização gerada pelo dispositivo. "
            "Payload: `{lat:.6f}|{lng:.6f}|{accuracy_m:.1f}|{geo_timestamp}`. "
            'Quando `accuracy_m` não for informado, substituir pelo literal `"null"` '
            "(ex: `-3.747361|-38.523060|null|1748166600`)."
        ),
        examples=["b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4"],
    )
    geo_timestamp: int = Field(
        gt=0,
        description="Unix timestamp (segundos desde epoch UTC) de quando a localização GPS foi capturada pelo dispositivo.",
        examples=[1748166600],
    )

    @field_validator("geo_signature")
    @classmethod
    def validate_geo_signature_is_hex(cls, value: str) -> str:
        if not all(c in "0123456789abcdef" for c in value.lower()):
            raise ValueError(
                "geo_signature deve ser um hash SHA-256 em formato hexadecimal."
            )
        return value.lower()


class QueueReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: UUID = Field(examples=[str(uuid4())])
    status: ReportStatusEnum = Field(examples=[ReportStatusEnum.SMALL.value])
    meal_period: MealPeriodEnum = Field(examples=[MealPeriodEnum.LUNCH.value])
    created_at: datetime = Field(examples=[datetime(2026, 5, 25, 10, 30, 0, tzinfo=UTC)])
