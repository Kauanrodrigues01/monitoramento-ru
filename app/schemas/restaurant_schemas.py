from datetime import UTC, datetime
from decimal import ROUND_DOWN, Decimal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.restaurant import CampusEnum


def _truncate_coordinates(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.000001"), rounding=ROUND_DOWN)


class RestaurantCreate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=3,
        max_length=120,
        examples=[f"RU {CampusEnum.PALMARES.value}"],
    )
    campus: CampusEnum = Field(
        description="Campus ao qual o restaurante pertence.",
        examples=[CampusEnum.PALMARES.value],
    )
    lat: Decimal = Field(ge=-90, le=90, examples=[-23.55052])
    lng: Decimal = Field(ge=-180, le=180, examples=[-46.63330])
    geofence_radius_m: int = Field(
        ge=0,
        le=120,
        default=80,
        description="Raio em metros usado para validar se um queue_report foi enviado dentro da área do restaurante.",
    )
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
        default=None,
        description="Campus ao qual o restaurante pertence.",
        examples=[CampusEnum.PALMARES.value],
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
        description="Raio em metros usado para validar se um queue_report foi enviado dentro da área do restaurante.",
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
    created_at: datetime = Field(examples=[datetime.now(UTC)])
    updated_at: datetime = Field(examples=[datetime.now(UTC)])
