# SIIS — Monitor Colaborativo do RU
## Checklist de Desenvolvimento — MVP

---

## ✅ Concluído

### Restaurants
- [x] Model, service, schemas, repository
- [x] Endpoints: `POST`, `GET (list)`, `GET (detail)`, `PATCH`
- [x] `POST` e `PATCH` requerem `ADMIN_API_KEY`
- [x] Testes de schemas e services

### Restaurant Schedules
- [x] Model, service, schemas, repository
- [x] Endpoints: `POST`, `GET (list)`, `PATCH`
- [x] `POST` e `PATCH` requerem `ADMIN_API_KEY`
- [x] Testes de schemas e services

### Restaurant Schedule Exceptions
- [x] Model, service, schemas, repository
- [x] Endpoints: `POST`, `GET (list)`, `PATCH`
- [x] `POST` e `PATCH` requerem `ADMIN_API_KEY`
- [x] Testes de schemas e services

### Queue Reports
- [x] Model, service, schemas, repository
- [x] Endpoint `POST` (público) com pipeline de validação:
  - [x] Restaurant existe e está ativo
  - [x] Assinatura HMAC com `APP_GEO_SECRET` — payload: `{lat:.6f}|{lng:.6f}|{accuracy_m:.1f}|{geo_timestamp}` — retorna `400` se inválida
  - [x] Janela temporal da assinatura: 60s por padrão (`GEO_SIGNATURE_MAX_SKEW_SECONDS` no `.env`)
  - [x] Cooldown por dispositivo (`device_hash`): 2 min por padrão (`QUEUE_REPORT_COOLDOWN_MINUTES` no `.env`) — header `X-Device-ID` obrigatório; resolve o problema de NAT em redes compartilhadas
  - [x] Verificação de horário de funcionamento (exceptions → schedules)
  - [x] Geofence (distância vs `geofence_radius_m` do restaurant)
- [x] Campos inferidos pelo servidor: `meal_period`, `ip_hash`, `device_hash`, `confidence_score`
- [x] Retorna `201` (sem async — evolui para `202` com Celery)
- [x] Endpoint `GET /v1/restaurants/{public_id}/reports/recent` — últimos 20 relatos do período vigente; response: `public_id`, `status`, `meal_period`, `created_at`
- [x] Testes de schemas e services

### Confidence Score Service
- [x] `is_mock_location = true` → −0.80
- [x] `accuracy_m` nulo ou 0 → −0.30
- [x] `accuracy_m` entre 20m e 50m → −0.15
- [x] Coordenadas com precisão suspeita (lat/lng redondos) → −0.25
- [x] Score mínimo: 0.05 (floor)

### Rate Limit (slowapi — `app/core/rate_limits.py`)
- [x] Aplicado a todos os endpoints
- [x] Chave efetiva: `X-Device-ID` → IP → `"anonymous"` (implementado em `app/core/rate_limiter.py`)

| Endpoint | Limite | Chave |
|---|---|---|
| `POST /restaurants` | 10 req/min | IP |
| `GET /restaurants` | 60 req/min | IP |
| `GET /restaurants/{id}` | 60 req/min | IP |
| `PATCH /restaurants/{id}` | 10 req/min | IP |
| `POST /restaurants/{id}/schedules` | 20 req/min | IP |
| `GET /restaurants/{id}/schedules` | 60 req/min | IP |
| `PATCH /restaurants/{id}/schedules/{sid}` | 20 req/min | IP |
| `POST /restaurants/{id}/schedule-exceptions` | 5 req/min | IP |
| `GET /restaurants/{id}/schedule-exceptions` | 60 req/min | IP |
| `PATCH /restaurants/{id}/schedule-exceptions/{eid}` | 10 req/min | IP |
| `POST /restaurants/{id}/reports` | 20 req/min (DoS bruto; cooldown real no service) | `X-Device-ID` |
| `GET /restaurants/{id}/reports/recent` | 60 req/min | IP |
| `GET /restaurants/status/bulk` | 20 req/min | IP |
| `GET /restaurants/{id}/status` | 60 req/min | IP |

### Queue Snapshots
- [x] Model `queue_snapshot`
- [x] Seed: cada restaurant recebe 2 snapshots (`LUNCH/NO_DATA`, `DINNER/NO_DATA`)
- [x] Criação automática dos snapshots junto com o restaurant (`POST /restaurants`)
- [x] Schemas, repository, service
- [x] Endpoints: `GET /v1/restaurants/{public_id}/status`, `GET /v1/restaurants/status/bulk`
- [x] Testes de schemas e service

### Cálculo de status do snapshot (`SnapshotStatusService`) — [spec](snapshot_status_spec.md)
- [x] Fórmula de média ponderada: `current_status = Σ(status_value × temporal_weight × confidence_score) / Σ(temporal_weight × confidence_score)`
- [x] Janela adaptativa: 5 min (≥5 relatos) / 10 min (≥3 relatos) / 15 min (demais)
- [x] Pesos temporais: ≤60s → 0.95 / ≤5min → 0.70 / ≤10min → 0.40 / >10min → 0.15
- [x] `FOOD_ENDED` com quórum separado: ≥3 relatos em 5 min sobrescreve o cálculo normal
- [x] `confidence_score` médio persistido no snapshot após cada recálculo
- [x] Atualização assíncrona via Background Tasks do FastAPI *(evolui para Celery task depois)*
- [x] Testes do `SnapshotStatusService`

### WebSocket — status em tempo real
- [x] Endpoint `WS /api/v1/ws/snapshots` — canal global; todos os restaurantes num único stream
- [x] A cada recálculo de snapshot: publica evento via Redis pub/sub → `WebSocketManager` transmite para todos os clientes conectados
- [x] Payload do evento `SnapshotUpdatedEvent`: `restaurant_public_id`, `meal_period`, `current_status`, `reports_last_15m`, `last_report_at`, `confidence_score`, `data_freshness_minutes`, `updated_at`
- [x] Rate limit: 20 conexões/min por IP (SlowAPI) + 1 conexão ativa por `device_id` (conexão antiga encerrada ao receber nova)
- [x] Testes: `WebSocketManager`, `pubsub`, `SnapshotWebSocketService`, endpoint e integração com `update_snapshot`

### Exceção de horário vigente
- [x] Endpoint `GET /v1/restaurants/{public_id}/schedule-exceptions/current` — público, 60 req/min
- [x] Retorna a exceção ativa para hoje e para o `meal_period` corrente, ou `{ "exception": null }`
- [x] Prioridade: `CLOSED` sem `meal_period` (dia inteiro) → `CLOSED/CUSTOM_HOURS` com `meal_period` correspondente
- [x] Testes: exceção `CLOSED` dia inteiro, `CUSTOM_HOURS` por período, sem exceção, fora do horário, restaurante inexistente

---

## 🔲 Pendente — ordenado por prioridade

### 1. Penalidade por divergência com o snapshot vigente (`ConfidenceScoreService`)

Usar `avg_status_value` do snapshot para penalizar relatos que divergem do consenso atual:

```python
distance = abs(STATUS_MAP_VALUE[report.status] - snapshot.avg_status_value)
if distance >= 2:     score -= 0.25   # divergência severa
elif distance >= 1.5: score -= 0.15   # divergência moderada
# sem penalidade se avg_status_value é null (NO_DATA ou FOOD_ENDED)
```

> O `ConfidenceScoreService` roda **antes** do recálculo de background — lê o snapshot do estado anterior ao relato, que é o consenso vigente no momento da chegada.

#### Model (`app/models/queue_snapshot.py`)
- [ ] Adicionar `avg_status_value: Mapped[float | None]` — `nullable=True`, sem default
- [ ] Adicionar `CheckConstraint("avg_status_value BETWEEN 0.0 AND 3.0 OR avg_status_value IS NULL", name="ck_avg_status_value_range")`
- [ ] `null` quando `current_status` é `NO_DATA` ou `FOOD_ENDED`

#### Migration (Alembic)
- [ ] `alembic revision --autogenerate -m "add avg_status_value to queue_snapshots"`
- [ ] Verificar: tipo `FLOAT`, `nullable=True`, sem `server_default`

#### `SnapshotStatusService`
- [ ] `_compute_status` passa a retornar `tuple[SnapshotStatusEnum, Decimal, float | None]`
  - Terceiro elemento: `total_weighted_value / total_weight` (antes do `round`) com scorable reports; `None` nos paths de `NO_DATA` e `FOOD_ENDED`
- [ ] Atualizar `calculate_snapshot_status` para desempacotar o terceiro elemento com `_`
- [ ] Atualizar `update_snapshot` para persistir `avg_status_value`

#### `ConfidenceScoreService`
- [ ] Adicionar parâmetro `snapshot: QueueSnapshot | None` ao método de cálculo
- [ ] Implementar penalidade — skip se `snapshot is None` ou `snapshot.avg_status_value is None`

#### `QueueReportService`
- [ ] Verificar ordem do pipeline — `meal_period` deve ser inferido **antes** do cálculo do score:
  `valida geofence → infere meal_period → busca snapshot → calcula confidence_score → persiste`
- [ ] Buscar snapshot via `snapshot_repo.get_by_ru_id_and_meal_period` após inferir `meal_period`
- [ ] Passar snapshot para `ConfidenceScoreService`

#### Schemas
- `avg_status_value` não será exposto na API — campo interno. Nenhuma alteração nos schemas.

#### Testes
- [ ] `test_queue_snapshot_model` — constraint `ck_avg_status_value_range`
- [ ] `test_snapshot_status_service` — `_compute_status` retorna valor bruto correto; `None` em `NO_DATA`/`FOOD_ENDED`; `update_snapshot` persiste o campo
- [ ] `test_confidence_score_service` — penalidade `−0.25` (distância ≥ 2), `−0.15` (≥ 1.5), sem penalidade com `avg_status_value = None` ou `snapshot = None`
- [ ] `test_queue_report_service` — snapshot buscado após `meal_period`, passado ao `ConfidenceScoreService`
- [ ] Atualizar testes de todas as classes que usam `ConfidenceScoreService` para incluir o parâmetro `snapshot`

### 2. Métricas gerais (`GET /v1/metrics/summary`)

Visão agregada do sistema para o painel principal do frontend.

```json
{
  "total_active_restaurants": 3,
  "open_now": 2,
  "reports_last_15m": 14,
  "status_distribution": {
    "NO_QUEUE": 1, "SMALL": 1, "MEDIUM": 0,
    "LARGE": 0, "FOOD_ENDED": 0, "NO_DATA": 1
  },
  "avg_confidence": 0.87
}
```

| Campo | Origem |
|---|---|
| `total_active_restaurants` | `COUNT` de `restaurants` com `is_active=true` |
| `open_now` | Snapshots com `meal_period` vigente |
| `reports_last_15m` | `SUM(reports_last_15m)` dos snapshots do período vigente |
| `status_distribution` | `COUNT GROUP BY current_status` dos snapshots vigentes |
| `avg_confidence` | Média de `confidence_score` dos snapshots com `current_status != NO_DATA` |

- [ ] Schema `MetricsSummaryResponse`
- [ ] `MetricsService.get_summary()` — queries diretas via `QueueSnapshotRepository` e `RestaurantRepository`; sem cache no MVP
- [ ] Endpoint público, rate limit 30 req/min
- [ ] Testes: contagem de ativos, `open_now`, `reports_last_15m`, `status_distribution`, `avg_confidence` exclui `NO_DATA`

### 3. Métricas por restaurante (`GET /v1/restaurants/{public_id}/metrics`)

Dados de atividade do dia corrente para a página de detalhe.

```json
{
  "reports_today": 42,
  "avg_confidence_today": 0.83,
  "status_history_today": [
    { "hour": 11, "meal_period": "LUNCH",  "dominant_status": "SMALL",  "report_count": 5 },
    { "hour": 12, "meal_period": "LUNCH",  "dominant_status": "LARGE",  "report_count": 12 },
    { "hour": 17, "meal_period": "DINNER", "dominant_status": "SMALL",  "report_count": 3 }
  ]
}
```

- `dominant_status` = status com maior soma de `confidence_score` na hora (moda ponderada)
- `status_history_today` alimenta gráfico de linha ou sparkline no frontend

- [ ] Schema `RestaurantMetricsResponse`, `StatusHistoryEntry`
- [ ] `QueueReportRepository.list_today_by_ru` — query com `created_at BETWEEN day_start AND day_end` (timezone `APP_TIMEZONE`)
- [ ] `MetricsService.get_restaurant_metrics(ru_id, day)` — agrupa por hora em Python
- [ ] Endpoint público, rate limit 30 req/min; retorna `404` se restaurante não existir; métricas zeradas se sem relatos hoje
- [ ] Testes: relatos do dia corrente no timezone correto, `avg_confidence_today = null` sem relatos, `dominant_status` por hora, `404` para restaurante inexistente

### 4. Refactoring
- [ ] Extrair `_get_restaurant_by_public_id_or_error` — duplicado em `QueueReportService`, `RestaurantScheduleService`, `RestaurantScheduleExceptionService` e `QueueSnapshotService`. Candidato a `RestaurantResolverMixin` ou `app/services/_utils.py`. Teste em `test_get_restaurant_or_error.py` já cobre o comportamento.
- [ ] Atualizar testes das classes afetadas

### 5. Testes de integração
- [ ] `restaurants.py`
- [ ] `restaurant_schedules.py`
- [ ] `restaurant_schedule_exceptions.py`
- [ ] `queue_reports.py`
- [ ] `queue_snapshots.py`

---

## 🔭 Melhorias futuras (pós-MVP)

### Observabilidade
- [ ] **structlog** — logs estruturados em JSON
- [ ] **Prometheus + Grafana** — métricas via `prometheus-fastapi-instrumentator` (`/metrics`)

### Processamento assíncrono

> **Broker:** RabbitMQ. Vantagens sobre Redis como broker: persistência de mensagens em disco, Dead Letter Queue nativa, Management UI em tempo real. Redis permanece exclusivo para cache.

#### Infraestrutura
- [ ] Serviço `rabbitmq` no Docker Compose (`rabbitmq:3-management`, porta 15672)
- [ ] Celery com `broker_url = amqp://...` e `result_backend = redis://...`
- [ ] Substituir Background Tasks por Celery task `update_snapshot_task(ru_id)` — `POST /reports` passa de `201` para `202 Accepted`
- [ ] `sqlalchemy-celery-beat` — scheduler dinâmico com schedules no PostgreSQL

#### `queue_aggregates_10m`
- [ ] Model: `ru_id`, `meal_period`, `weekday`, `bucket_start`, `bucket_end`, `avg_status`, `avg_confidence`, `report_count`, `food_ended_count`
  - PK composta: `(ru_id, meal_period, bucket_start)`
  - `bucket_start` sempre no grid global de 10 min (00:00, 00:10 ... 23:50)
  - `weekday` via `EXTRACT(DOW FROM bucket_start)`
  - Índice: `(ru_id, weekday, meal_period)` para queries de heatmap
- [ ] Repository: `upsert_bucket`, `list_by_ru_and_period`, `list_for_heatmap`
- [ ] Schemas para endpoint de previsão
- [ ] Testes do model e repository

#### Tasks
- [ ] **`close_meal_period_task(ru_id, meal_period, opens_at, closes_at)`** — ao atingir `closes_at`: enfileira `aggregate_meal_period_task` se houve relatos; reseta snapshot para `NO_DATA`; invalida cache Redis; publica `RU_CLOSED` via WebSocket
- [ ] **`aggregate_meal_period_task(ru_id, meal_period, opens_at, closes_at)`** — processa relatos do período em buckets fixos de 10 min; UPSERT em `queue_aggregates_10m`
- [ ] **`FOOD_ENDED` override via Redis** — TTL explícito `min(30 min, tempo até closes_at)` em vez de remoção implícita por janela
- [ ] **`sync_scheduled_tasks(ru_id, target_date)`** — no startup e a cada alteração de schedules: cria/atualiza `PeriodicTask` com `ClockedSchedule` para o `closes_at` de cada slot
- [ ] Testes das tasks

#### Job 2 — Cache semanal (domingos às 02:00)
- [ ] Lê `queue_aggregates_10m`; aplica `normalize_for_query(opens_at, closes_at, bucket_size=10)`; calcula médias; salva no Redis `analytics:ru:{id}:weekly` (TTL 7 dias)
- [ ] Endpoint `GET /v1/restaurants/{public_id}/prediction`

#### Job 3 — Limpeza de dados *(em avaliação)*
- [ ] Política: 90 dias para `queue_reports`, 365 dias para `queue_aggregates_10m` e `admin_audit_log`
- [ ] Definir implementação: CrontabSchedule (Celery), pg_cron, ou script manual

### Confidence score — penalidades históricas
- [ ] IP com histórico inconsistente *(requer `queue_aggregates_10m` populado)*
- [ ] Relato inconsistente com histórico recente do RU *(idem)*

### Resiliência
- [ ] Timeouts em cascata: `statement_timeout` (PostgreSQL), `socket_timeout` (Redis), `httpx.Timeout`, `--timeout-keep-alive` (uvicorn)

### Segurança
- [ ] HTTP Security Headers: `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`

---

## 📝 Decisões que divergem do escopo (intencionais)

| Item | Escopo | Implementado | Justificativa |
|---|---|---|---|
| Status HMAC inválido | 401 | 400 | Validação de payload, não autenticação |
| Status criação report | 202 | 201 | Sem async no MVP — evolui para 202 com Celery |
| Chave de cooldown | IP | `device_hash` | Resolve NAT em redes compartilhadas |
| Penalidade lat/lng redondo | −0.15 | −0.25 | Escopo atualizado |
| `geo_sig_valid` | Campo no banco | Removido | Invariante — sempre `true` |
| Recálculo snapshot | Celery | Background Tasks FastAPI | Bridge para MVP |
| Expiração `FOOD_ENDED` | TTL Redis | Janela implícita de 5 min | Sem Redis no MVP — evolui com Celery |
| Broker Celery | Redis | RabbitMQ | Persistência, DLQ e visibilidade |