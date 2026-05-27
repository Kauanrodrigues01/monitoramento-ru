from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.queue_snapshot import SnapshotStatusEnum
from app.models.restaurant import MealPeriodEnum


class QueueSnapshotOverride(BaseModel):
    current_status: SnapshotStatusEnum = Field(
        description="Status da fila a ser aplicado manualmente.",
        examples=[SnapshotStatusEnum.LARGE.value],
    )
    override_active: bool = Field(
        description=(
            "Ativa ou desativa o override manual. "
            "Quando True, o serviço não sobrescreve o status com novos relatos."
        ),
        examples=[True],
    )


class QueueSnapshotBulkItem(BaseModel):
    restaurant_public_id: UUID = Field(
        description="ID público do restaurante.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    meal_period: MealPeriodEnum = Field(
        description="Período de refeição ativo no momento da consulta.",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    current_status: SnapshotStatusEnum = Field(
        description="Status atual da fila do restaurante.",
        examples=[SnapshotStatusEnum.NO_DATA.value],
    )
    reports_last_15m: int = Field(
        description="Número de relatos recebidos nos últimos 15 minutos.",
        examples=[3],
    )
    last_report_at: datetime | None = Field(
        description="Data e hora do último relato recebido.",
        examples=[datetime(2026, 5, 26, 11, 45, 0, tzinfo=UTC)],
    )
    updated_at: datetime = Field(
        description="Data e hora da última atualização do snapshot.",
        examples=[datetime(2026, 5, 26, 11, 45, 0, tzinfo=UTC)],
    )


class QueueSnapshotResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_period: MealPeriodEnum = Field(
        description="Período da refeição do snapshot.",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    current_status: SnapshotStatusEnum = Field(
        description="Status atual da fila do restaurante.",
        examples=[SnapshotStatusEnum.NO_DATA.value],
    )
    reports_last_15m: int = Field(
        description="Número de relatos recebidos nos últimos 15 minutos.",
        examples=[3],
    )
    last_report_at: datetime | None = Field(
        description="Data e hora do último relato recebido.",
        examples=[datetime(2026, 5, 26, 11, 45, 0, tzinfo=UTC)],
    )
    updated_at: datetime = Field(
        description="Data e hora da última atualização do snapshot.",
        examples=[datetime(2026, 5, 26, 11, 45, 0, tzinfo=UTC)],
    )
