from pydantic import BaseModel, Field


class MetricsSummaryResponse(BaseModel):
    total_active_restaurants: int = Field(
        description="Número total de restaurantes ativos"
    )
    open_now: int = Field(description="Número de restaurantes abertos no momento")
    reports_last_15m: int = Field(
        description="Número de relatos nos últimos 15 minutos"
    )
    reports_today: int = Field(description="Número de relatos do dia corrente")
    status_distribution: dict[str, int] = Field(
        description="Distribuição de status dos restaurantes"
    )
    avg_confidence: float | None = Field(
        description="Pontuação média de confiabilidade"
    )
