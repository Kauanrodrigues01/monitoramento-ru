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
  - [x] Cooldown por dispositivo (`device_hash`): 2 min por padrão (`QUEUE_REPORT_COOLDOWN_MINUTES` no `.env`) — header `X-Device-ID` obrigatório; resolve NAT em redes compartilhadas
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
- [x] Divergência com `avg_status_value` do snapshot: distância ≥ 2 → −0.25; distância ≥ 1.5 → −0.15
- [x] Score mínimo: 0.05 (floor)
- [x] Testes de schemas e services

### Rate Limit (slowapi — `app/core/rate_limits.py`)
- [x] Aplicado a todos os endpoints
- [x] Chave efetiva: `X-Device-ID` → IP → `"anonymous"` (`app/core/rate_limiter.py`)

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
- [x] Model `queue_snapshot` com `avg_status_value: Mapped[Decimal | None]` (`Numeric(3,2)`, nullable)
- [x] `CheckConstraint` em `avg_status_value`: `NULL` ou entre `0.00` e `3.00`
- [x] Seed: cada restaurant recebe 2 snapshots (`LUNCH/NO_DATA`, `DINNER/NO_DATA`)
- [x] Criação automática dos snapshots junto com o restaurant (`POST /restaurants`)
- [x] Schemas, repository, service
- [x] Endpoints: `GET /v1/restaurants/{public_id}/status`, `GET /v1/restaurants/status/bulk`
- [x] Testes de schemas e service

### Cálculo de status do snapshot (`SnapshotStatusService`) — [spec](snapshot_status_spec.md)
- [x] Fórmula: `current_status = Σ(status_value × temporal_weight × confidence_score) / Σ(temporal_weight × confidence_score)`
- [x] Janela adaptativa: 5 min (≥5 relatos) / 10 min (≥3 relatos) / 15 min (demais)
- [x] Pesos temporais: ≤60s → 0.95 / ≤5min → 0.70 / ≤10min → 0.40 / >10min → 0.15
- [x] `FOOD_ENDED` com quórum separado: ≥3 relatos em 5 min sobrescreve o cálculo normal
- [x] `_compute_status` retorna `tuple[SnapshotStatusEnum, Decimal, Decimal | None]` — terceiro elemento é `avg_status_value`; `None` em `NO_DATA` e `FOOD_ENDED`
- [x] `confidence_score` e `avg_status_value` persistidos no snapshot após cada recálculo
- [x] Atualização assíncrona via Background Tasks do FastAPI *(evolui para Celery task depois)*
- [x] Testes do `SnapshotStatusService`

### WebSocket — status em tempo real
- [x] Endpoint `WS /api/v1/ws/snapshots` — canal global; todos os restaurantes num único stream
- [x] A cada recálculo de snapshot: publica via Redis pub/sub → `WebSocketManager` transmite para clientes conectados
- [x] Payload `SnapshotUpdatedEvent`: `restaurant_public_id`, `meal_period`, `current_status`, `reports_last_15m`, `last_report_at`, `confidence_score`, `data_freshness_minutes`, `updated_at`
- [x] Rate limit: 20 conexões/min por IP + 1 conexão ativa por `device_id` (conexão antiga encerrada ao receber nova)
- [x] Testes: `WebSocketManager`, `pubsub`, `SnapshotWebSocketService`, endpoint, integração com `update_snapshot`

### Exceção de horário vigente
- [x] Endpoint `GET /v1/restaurants/{public_id}/schedule-exceptions/current` — público, 60 req/min
- [x] Retorna exceção ativa para hoje e `meal_period` corrente, ou `{ "exception": null }`
- [x] Prioridade: `CLOSED` sem `meal_period` (dia inteiro) → `CLOSED/CUSTOM_HOURS` com `meal_period` correspondente
- [x] Testes: `CLOSED` dia inteiro, `CUSTOM_HOURS` por período, sem exceção, fora do horário, restaurante inexistente

### Métricas gerais
- [x] Endpoint `GET /v1/metrics/summary` — público, 30 req/min
- [x] Schema `MetricsSummaryResponse`: `total_active_restaurants`, `open_now`, `reports_last_15m`, `reports_today`, `status_distribution`, `avg_confidence`
- [x] `MetricsService.get_summary()` — queries diretas via repositórios; sem cache no MVP
- [x] Testes

### Observabilidade — Prometheus
- [x] Métricas HTTP automáticas via `prometheus-fastapi-instrumentator`
- [x] Endpoint `/metrics`
- [x] Métricas customizadas de reports: `queue_reports_created_total`, `queue_reports_rejected_total`, `queue_reports_confidence_score`, `queue_report_distance_meters`
- [x] Métricas de negócio: `business_requests_total`, `rate_limit_blocked_total`
- [x] Instrumentação das metricas no `QueueReportService` e `SlowAPI` (via exception handler de `RateLimitExceeded`)
- [x] Middleware para instrumentação da metrica `business_requests_total` que pega apenas os endpoints de negócio usando as tags dos routers e exclui `/metrics`, WebSockets, debug, health checks e etc...
- [x] Health checks: `GET /health/live`, `GET /health/ready`
- [x] Ambiente de desenvolvimento com Grafana via Docker Compose

### Refactoring
- [x] Extraído `_get_restaurant_by_public_id_or_error` — centralizado em `app/services/_utils.py`
- [x] Testes das classes afetadas atualizados

### Testes com banco real

#### Models — constraints e invariantes
- [x] `QueueSnapshot.ck_avg_status_value_range` — rejeita valores fora de `[0.00, 3.00]`; aceita `NULL`
- [x] `QueueReport.ck_confidence_score_range` — rejeita valores fora de `[0.05, 1.00]`
- [x] `Restaurant` — `public_id` UUID único; `is_active = True` por padrão
- [x] `RestaurantSchedule` — `opens_at < closes_at`; `meal_period` é enum
- [x] `RestaurantScheduleException` — `opens_at < closes_at` para `CUSTOM_HOURS`; `meal_period` nullable
- [x] Cascade `ondelete` — deletar `Restaurant` remove `QueueSnapshot` e `QueueReport`

#### Repositories — queries
- [x] `QueueReportRepository`
- [x] `QueueSnapshotRepository`
- [x] `RestaurantRepository`
- [x] `RestaurantScheduleRepository`
- [x] `RestaurantScheduleExceptionRepository`

---

## 🔲 Pendente — ordenado por prioridade

### 1. Observabilidade — Prometheus
- [ ] Adicionar testes para os arquivos em app/core/observability
- [ ] Atualizar testes de QueueReportService para verificar incrementos nas métricas Prometheus

### 2. Testes de integração (endpoints)

> Requerem PostgreSQL + Redis rodando. Adicionar serviços ao CI antes de habilitar.

- [ ] `restaurants.py`
- [ ] `restaurant_schedules.py`
- [ ] `restaurant_schedule_exceptions.py`
- [ ] `queue_reports.py`
- [ ] `queue_snapshots.py`

### 3. Observabilidade — Grafana
- [ ] Integração com Prometheus como datasource
- [ ] Dashboards para monitoramento da API e métricas de negócio


---

## 🔭 Melhorias futuras (pós-MVP)

### Observabilidade
- [ ] **structlog** — logs estruturados em JSON

### Processamento assíncrono

> **Broker:** RabbitMQ em vez de Redis. Persistência de mensagens em disco, Dead Letter Queue nativa e Management UI em tempo real. Redis permanece exclusivo para cache.

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
- [ ] **`close_meal_period_task`** — ao atingir `closes_at`: enfileira `aggregate_meal_period_task` se houve relatos; reseta snapshot para `NO_DATA`; invalida cache Redis; publica `RU_CLOSED` via WebSocket
- [ ] **`aggregate_meal_period_task`** — processa relatos do período em buckets fixos de 10 min; UPSERT em `queue_aggregates_10m`
- [ ] **`FOOD_ENDED` override via Redis** — TTL explícito `min(30 min, tempo até closes_at)` em vez de remoção implícita por janela
- [ ] **`sync_scheduled_tasks`** — no startup e a cada alteração de schedules: cria/atualiza `PeriodicTask` com `ClockedSchedule` para o `closes_at` de cada slot
- [ ] Testes das tasks

#### Jobs periódicos
- [ ] **Job 2 — Cache semanal** (domingos às 02:00): lê `queue_aggregates_10m`, aplica `normalize_for_query(opens_at, closes_at, bucket_size=10)`, salva no Redis `analytics:ru:{id}:weekly` (TTL 7 dias). Endpoint: `GET /v1/restaurants/{public_id}/prediction`
- [ ] **Job 3 — Limpeza de dados** *(em avaliação)*: 90 dias para `queue_reports`, 365 dias para `queue_aggregates_10m` e `admin_audit_log`. Implementação a definir: Celery CrontabSchedule, pg_cron ou script manual

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