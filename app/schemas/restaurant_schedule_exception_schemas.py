from datetime import date, datetime, time
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.restaurant import ExceptionTypeEnum, MealPeriodEnum


class RestaurantScheduleExceptionCreate(BaseModel):
    exception_date: date = Field(
        description="Data da exceção.",
        examples=["2025-12-25"],
    )
    exception_type: ExceptionTypeEnum = Field(
        description="Tipo da exceção: CLOSED (RU fechado) ou CUSTOM_HOURS (horário diferente do padrão).",
        examples=[ExceptionTypeEnum.CLOSED.value],
    )
    meal_period: MealPeriodEnum | None = Field(
        default=None,
        description="Período afetado. Null indica que a exceção se aplica ao dia inteiro.",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    opens_at: time | None = Field(
        default=None,
        description="Horário de abertura. Obrigatório quando exception_type = CUSTOM_HOURS.",
        examples=["11:00"],
    )
    closes_at: time | None = Field(
        default=None,
        description="Horário de fechamento. Obrigatório quando exception_type = CUSTOM_HOURS.",
        examples=["14:00"],
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
        description="Motivo da exceção (opcional).",
        examples=["Feriado nacional"],
    )

    @model_validator(mode="after")
    def validate_custom_hours(self):
        if self.exception_type == ExceptionTypeEnum.CUSTOM_HOURS:
            if self.opens_at is None or self.closes_at is None:
                raise ValueError(
                    "opens_at e closes_at são obrigatórios quando exception_type = CUSTOM_HOURS."
                )
            if self.opens_at >= self.closes_at:
                raise ValueError(
                    "Horário de abertura deve ser anterior ao horário de fechamento."
                )
        if self.exception_type == ExceptionTypeEnum.CLOSED:
            if self.opens_at is not None or self.closes_at is not None:
                raise ValueError(
                    "opens_at e closes_at não devem ser informados quando exception_type = CLOSED."
                )
        return self


class RestaurantScheduleExceptionUpdate(BaseModel):
    exception_type: ExceptionTypeEnum | None = Field(
        default=None,
        description="Tipo da exceção: CLOSED (RU fechado) ou CUSTOM_HOURS (horário diferente do padrão).",
        examples=[ExceptionTypeEnum.CLOSED.value],
    )
    meal_period: MealPeriodEnum | None = Field(
        default=None,
        description="Período afetado. Null indica que a exceção se aplica ao dia inteiro.",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    opens_at: time | None = Field(
        default=None,
        description="Horário de abertura. Obrigatório quando exception_type = CUSTOM_HOURS.",
        examples=["11:00"],
    )
    closes_at: time | None = Field(
        default=None,
        description="Horário de fechamento. Obrigatório quando exception_type = CUSTOM_HOURS.",
        examples=["14:00"],
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
        description="Motivo da exceção (opcional).",
        examples=["Feriado nacional"],
    )


class RestaurantScheduleExceptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: UUID = Field(examples=[str(uuid4())])
    exception_date: date = Field(examples=["2025-12-25"])
    exception_type: ExceptionTypeEnum = Field(examples=[ExceptionTypeEnum.CLOSED.value])
    meal_period: MealPeriodEnum | None = Field(examples=[MealPeriodEnum.LUNCH.value])
    opens_at: time | None = Field(examples=["11:00"])
    closes_at: time | None = Field(examples=["14:00"])
    reason: str | None = Field(examples=["Feriado nacional"])
    created_at: datetime = Field(examples=[datetime.now()])
    updated_at: datetime = Field(examples=[datetime.now()])
