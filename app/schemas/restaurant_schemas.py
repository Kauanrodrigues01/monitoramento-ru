from datetime import datetime, time
from decimal import ROUND_DOWN, Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.restaurant import CampusEnum, MealPeriodEnum


def _truncate_coordinates(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


class RestaurantCreate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
        examples=[f"RU {CampusEnum.PALMARES.value}"],
    )
    campus: CampusEnum = Field(examples=[CampusEnum.PALMARES.value])
    lat: Decimal = Field(ge=-90, le=90, examples=[-23.55052])
    lng: Decimal = Field(ge=-180, le=180, examples=[-46.63330])
    geofence_radius_m: int = Field(ge=0, le=120, default=80)
    is_active: bool = True

    @field_validator("lat", "lng")
    @classmethod
    def truncate_coordinates(cls, value: Decimal) -> Decimal:
        return _truncate_coordinates(value)

    @model_validator(mode="after")
    def set_default_name(self):
        if self.name is None:
            self.name = f"RU {self.campus.value}"
        return self


class RestaurantUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
        examples=[f"RU {CampusEnum.PALMARES.value}"],
    )
    campus: CampusEnum | None = Field(
        default=None, examples=[CampusEnum.PALMARES.value]
    )
    lat: Decimal | None = Field(
        ge=-90,
        le=90,
        default=None,
        examples=[-23.55052],
    )
    lng: Decimal | None = Field(
        ge=-180,
        le=180,
        default=None,
        examples=[-46.63330],
    )
    geofence_radius_m: int | None = Field(
        ge=0,
        le=120,
        default=None,
    )
    is_active: bool | None = None

    @field_validator("lat", "lng")
    @classmethod
    def truncate_coordinates(cls, value: Decimal | None) -> Decimal | None:
        if value is None:
            return value
        return _truncate_coordinates(value)


class RestaurantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: UUID = Field(examples=[str(uuid4())])
    name: str = Field(examples=[f"RU {CampusEnum.PALMARES.value}"])
    campus: CampusEnum = Field(examples=[CampusEnum.PALMARES.value])
    lat: Decimal = Field(examples=[-23.55052])
    lng: Decimal = Field(examples=[-46.63330])
    geofence_radius_m: int = Field(examples=[80])
    is_active: bool = Field(examples=[True])
    created_at: datetime = Field(examples=[datetime.now()])
    updated_at: datetime = Field(examples=[datetime.now()])


class RestaurantScheduleCreate(BaseModel):
    weekday: int = Field(
        ge=0,
        le=5,
        examples=[0, 1, 2, 3, 4, 5],
    )
    meal_period: MealPeriodEnum = Field(examples=[MealPeriodEnum.LUNCH.value])
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


class RestaurantScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    public_id: UUID = Field(examples=[str(uuid4())])
    weekday: int = Field(
        ge=0,
        le=5,
        examples=[0, 1, 2, 3, 4, 5],
    )
    meal_period: MealPeriodEnum = Field(examples=[MealPeriodEnum.LUNCH.value])
    opens_at: time = Field(examples=["11:00"])
    closes_at: time = Field(examples=["14:00"])
    is_active: bool
    created_at: datetime = Field(examples=[datetime.now()])
    updated_at: datetime = Field(examples=[datetime.now()])


class RestaurantScheduleUpdate(BaseModel):
    weekday: int | None = Field(ge=0, le=5, examples=[0, 1, 2, 3, 4, 5], default=None)
    meal_period: MealPeriodEnum | None = Field(
        default=None, examples=[MealPeriodEnum.LUNCH.value]
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
