from datetime import datetime, time
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.restaurant import MealPeriodEnum


class RestaurantScheduleCreate(BaseModel):
    weekday: int = Field(
        ge=0,
        le=5,
        description="Dia da semana: 0 = segunda-feira, 5 = sábado.",
        examples=[0, 1, 2, 3, 4, 5],
    )
    meal_period: MealPeriodEnum = Field(
        description="Período da refeição (almoço ou jantar).",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    opens_at: time = Field(examples=["11:00"])
    closes_at: time = Field(examples=["14:00"])
    is_active: bool = True

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.opens_at >= self.closes_at:
            raise ValueError(
                "Horário de abertura deve ser anterior ao horário de fechamento."
            )
        return self


class RestaurantScheduleUpdate(BaseModel):
    weekday: int | None = Field(
        ge=0,
        le=5,
        default=None,
        description="Dia da semana: 0 = segunda-feira, 5 = sábado.",
        examples=[0, 1, 2, 3, 4, 5],
    )
    meal_period: MealPeriodEnum | None = Field(
        default=None,
        description="Período da refeição (almoço ou jantar).",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    opens_at: time | None = Field(default=None, examples=["11:00"])
    closes_at: time | None = Field(default=None, examples=["14:00"])
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_time_range(self):
        if (
            self.opens_at is not None
            and self.closes_at is not None
            and self.opens_at >= self.closes_at
        ):
            raise ValueError(
                "Horário de abertura deve ser anterior ao horário de fechamento."
            )
        return self


class RestaurantScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: UUID = Field(examples=[str(uuid4())])
    weekday: int = Field(
        ge=0,
        le=5,
        description="Dia da semana: 0 = segunda-feira, 5 = sábado.",
        examples=[0, 1, 2, 3, 4, 5],
    )
    meal_period: MealPeriodEnum = Field(
        description="Período da refeição (almoço ou jantar).",
        examples=[MealPeriodEnum.LUNCH.value],
    )
    opens_at: time = Field(examples=["11:00"])
    closes_at: time = Field(examples=["14:00"])
    is_active: bool
    created_at: datetime = Field(examples=[datetime.now()])
    updated_at: datetime = Field(examples=[datetime.now()])
