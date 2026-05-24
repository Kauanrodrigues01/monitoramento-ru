from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    detail: str = Field(examples=["Erro de aplicação"])
