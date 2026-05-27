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
  - [x] Cooldown por IP: 2 min por padrão (`QUEUE_REPORT_COOLDOWN_MINUTES` no `.env`)
  - [x] Verificação de horário de funcionamento (exceptions → schedules)
  - [x] Geofence (distância vs `geofence_radius_m` do restaurant)
- [x] Campos inferidos pelo servidor: `meal_period`, `ip_hash`, `confidence_score`
- [x] Retorna `201` (sem async ainda — evolui para `202` com Celery)
- [x] Endpoint `GET /v1/restaurants/{public_id}/reports/recent` — últimos 20 relatos do período vigente
- [x] Response: apenas `public_id`, `status`, `meal_period`, `created_at`
- [x] Testes de schemas e services

### Confidence Score Service
- [x] `is_mock_location = true` → −0.80
- [x] `accuracy_m` nulo ou 0 → −0.30
- [x] `accuracy_m` entre 20m e 50m → −0.15
- [x] Coordenadas com precisão suspeita (lat/lng redondos) → −0.25
- [x] Score mínimo: 0.05 (floor)
- [ ] IP com histórico de relatos inconsistentes *(pendente — requer dados históricos)*
- [ ] Relato inconsistente com histórico recente do RU *(pendente — requer snapshot funcional)*

### Rate Limit (slowapi)
- [x] Aplicado a todos os endpoints da aplicação

**Regras definidas** (`app/core/rate_limits.py`):

| Operação | Limite |
|---|---|
| `POST /restaurants` | 10 req/min por IP |
| `GET /restaurants` | 60 req/min por IP |
| `GET /restaurants/{id}` | 60 req/min por IP |
| `PATCH /restaurants/{id}` | 10 req/min por IP |
| `POST /restaurants/{id}/schedules` | 20 req/min por IP |
| `GET /restaurants/{id}/schedules` | 60 req/min por IP |
| `PATCH /restaurants/{id}/schedules/{sid}` | 20 req/min por IP |
| `POST /restaurants/{id}/schedule-exceptions` | 5 req/min por IP |
| `GET /restaurants/{id}/schedule-exceptions` | 60 req/min por IP |
| `PATCH /restaurants/{id}/schedule-exceptions/{eid}` | 10 req/min por IP |
| `POST /restaurants/{id}/reports` | 20 req/min por IP (DoS bruto; cooldown real no service) |
| `GET /restaurants/{id}/reports/recent` | 60 req/min por IP |
| `GET /restaurants/status/bulk` | 20 req/min por IP |
| `GET /restaurants/{id}/status` | 60 req/min por IP |

### Queue Snapshots
- [x] Model `queue_snapshot`
- [x] Seed: cada restaurant recebe 2 snapshots (`LUNCH/NO_DATA`, `DINNER/NO_DATA`)
- [x] Criação automática dos snapshots junto com o restaurant (`POST /restaurants`)
- [x] Schemas, repository, service
- [x] Endpoint: `GET /v1/restaurants/{public_id}/status`
- [x] Endpoint: `GET /v1/restaurants/status/bulk?ids=uuid1,uuid2,...`
- [x] Testes de schemas
- [x] Testes de service

### Cálculo de status do snapshot (`SnapshotStatusService`) — [spec](snapshot_status_spec.md)
- [x] Fórmula de média ponderada:
  ```
  peso_final       = confidence_score × peso_temporal
  status_ponderado = status_value × peso_final
  current_status   = Σ(status_ponderado) / Σ(peso_final)
  ```
- [x] Janela adaptativa: 5 min (≥5 relatos), 10 min (≥3 relatos), 15 min (demais)
- [x] Pesos temporais: ≤60s → 0.95 / ≤5min → 0.70 / ≤10min → 0.40 / >10min → 0.15
- [x] `FOOD_ENDED` com lógica de quórum separada: ≥3 relatos em 5 min sobrescreve o cálculo normal
- [x] `confidence_score` médio persistido no snapshot após cada recálculo
- [x] Atualização assíncrona via Background Tasks do FastAPI após criação de report *(evolui para Celery task depois)*
- [x] Testes do `SnapshotStatusService`

---

## 🔲 Pendente — ordenado por prioridade

### 1. Penalidade por divergência com o snapshot vigente (`ConfidenceScoreService`)

Usar `avg_status_value` do snapshot para penalizar relatos que divergem do consenso atual:

```python
distance = abs(STATUS_MAP_VALUE[report.status] - snapshot.avg_status_value)
if distance >= 2:     score -= 0.25   # divergência severa (ex: LARGE quando snapshot é NO_QUEUE)
elif distance >= 1.5: score -= 0.15   # divergência moderada
# sem penalidade se avg_status_value é null (NO_DATA ou FOOD_ENDED)
```

> O `ConfidenceScoreService` roda **antes** do recálculo de background — lê o snapshot do estado anterior ao relato, que é exatamente o consenso vigente no momento da chegada.

#### Model (`app/models/queue_snapshot.py`)
- [ ] Adicionar coluna `avg_status_value: Mapped[float | None]` — `nullable=True`, sem default
- [ ] Adicionar `CheckConstraint("avg_status_value BETWEEN 0.0 AND 3.0 OR avg_status_value IS NULL", name="ck_avg_status_value_range")`
- [ ] `null` quando `current_status` é `NO_DATA` ou `FOOD_ENDED` (sem valor contínuo significativo)

#### Migration (Alembic)
- [ ] Gerar migration: `alembic revision --autogenerate -m "add avg_status_value to queue_snapshots"`
- [ ] Verificar migration gerada — confirmar tipo `FLOAT`, `nullable=True`, sem server_default

#### `SnapshotStatusService` (`app/services/snapshot_status_service.py`)
- [ ] Atualizar `_compute_status` para retornar `tuple[SnapshotStatusEnum, Decimal, float | None]` — terceiro elemento é `avg_status_value`
  - Calcular como `total_weighted_value / total_weight` (antes do `round`) quando há scorable reports
  - Retornar `None` nos paths de `NO_DATA` e `FOOD_ENDED`
- [ ] Atualizar `calculate_snapshot_status` para desempacotar o terceiro elemento com `_`
- [ ] Atualizar `update_snapshot` para desempacotar e persistir `snapshot.avg_status_value = new_avg_status_value`

#### `ConfidenceScoreService` (`app/services/confidence_score_service.py`)
- [ ] Adicionar parâmetro `snapshot: QueueSnapshot | None` ao método de cálculo (ou ao `__init__` se for stateless)
- [ ] Implementar penalidade de distância conforme fórmula acima — skip se `snapshot` for `None` ou `snapshot.avg_status_value` for `None`

#### `QueueReportService` (`app/services/queue_report_service.py`)
- [ ] Verificar a ordem do pipeline antes de implementar — o fluxo atual é:
  `valida geofence → calcula confidence_score → infere meal_period → persiste`
  Para buscar o snapshot é necessário o `meal_period`. Se o confidence score é calculado **antes** da inferência do `meal_period`, reordenar para:
  `valida geofence → infere meal_period → busca snapshot → calcula confidence_score → persiste`
- [ ] Buscar snapshot vigente via `snapshot_repo.get_by_ru_id_and_meal_period` com `ru_id` e `meal_period` já inferido
- [ ] Passar snapshot para `ConfidenceScoreService` no cálculo do score do novo relato

#### Schemas (`app/schemas/queue_snapshot_schemas.py`)
- `avg_status_value` **não será exposto na API** — é detalhe de implementação do cálculo; o frontend não tem uso direto para um float entre 0 e 3. O `current_status` enum já comunica o estado de forma legível. Se futuramente um dashboard admin precisar, pode ser adicionado como campo admin naquele momento. Nenhuma alteração nos schemas.

#### Testes
- [ ] `test_queue_snapshot_model` — verificar constraint `ck_avg_status_value_range`
- [ ] `test_snapshot_status_service.py`:
  - `_compute_status` retorna `avg_status_value` correto (valor bruto antes do round) nos paths de scorable reports
  - `_compute_status` retorna `None` nos paths de `NO_DATA` e `FOOD_ENDED`
  - `update_snapshot` persiste `avg_status_value` no snapshot
- [ ] `test_confidence_score_service.py`:
  - Penalidade `−0.25` quando distância `≥ 2`
  - Penalidade `−0.15` quando distância `≥ 1.5`
  - Sem penalidade quando `avg_status_value` é `None`
  - Sem penalidade quando snapshot é `None` (estado `NO_DATA`)
- [ ] `test_queue_report_service.py` (ou `test_create_queue_report.py`):
  - Snapshot vigente é buscado antes do cálculo do score
  - Snapshot é passado ao `ConfidenceScoreService`
- [ ] Schemas: atualizar testes se `avg_status_value` for exposto na API

### 2. Revisões de confidence score (demais pendências)
- [ ] Implementar: IP com histórico de relatos inconsistentes *(requer `queue_aggregates_10m` — pós-MVP)*
- [ ] Implementar: Relato inconsistente com histórico recente do RU *(idem)*

### 3. Testes de integração
- [ ] Endpoints de `restaurants.py`
- [ ] Endpoints de `restaurant_schedules.py`
- [ ] Endpoints de `restaurant_schedule_exceptions.py`
- [ ] Endpoints de `queue_reports.py`
- [ ] Endpoints de `queue_snapshots.py`

---

## 🔭 Melhorias futuras (pós-MVP)

### Refactoring
- [ ] **Extrair `_get_restaurant_by_public_id_or_error`** — método privado duplicado em `QueueReportService`, `RestaurantScheduleService`, `RestaurantScheduleExceptionService` e `QueueSnapshotService`. Candidato a `RestaurantResolverMixin` ou função utilitária em `app/services/_utils.py`. Teste isolado em `test_get_restaurant_or_error.py` já cobre o comportamento e pode ser reaproveitado.

### Processamento assíncrono
- [ ] **Celery + Redis Broker** — substituir Background Tasks do FastAPI por Celery para o recálculo do snapshot. Retorno do `POST /reports` passa de `201` para `202 Accepted`
- [ ] **sqlalchemy-celery-beat** — scheduler dinâmico com schedules persistidos no PostgreSQL
- [ ] **`close_meal_period_task`** — disparada pelo beat no `closes_at` de cada slot: encerra o período, reseta snapshot para `NO_DATA`, invalida Redis, publica evento WebSocket
- [ ] **`aggregate_meal_period_task`** — enfileirada por `close_meal_period_task` quando o período teve relatos: processa buckets fixos de 10 min e grava em `queue_aggregates_10m`
- [ ] **`FOOD_ENDED` override via Redis** — substituir a remoção implícita por janela (comportamento atual) por TTL explícito no Redis: `min(30 min, tempo restante até closes_at)`. Garante expiração precisa independente de novos relatos chegarem
- [ ] **Job 2 — Cache semanal** — CrontabSchedule aos domingos: lê `queue_aggregates_10m`, aplica `normalize_for_query`, salva no Redis (`analytics:ru:{id}:weekly`, TTL 7 dias)
- [ ] **Job 3 — Limpeza de dados** — CrontabSchedule às segundas: aplica política de retenção (90 dias para `queue_reports`, 365 dias para `queue_aggregates_10m` e `admin_audit_log`)

### Observabilidade
- [ ] **structlog** — substituir o logger padrão por structlog para logs estruturados em JSON
- [ ] **Prometheus + Grafana** — expor métricas via `prometheus-fastapi-instrumentator` (`/metrics`) e criar dashboards de latência, taxa de erros e volume de relatos por RU

### Resiliência
- [ ] **Timeouts em cascata** — configurar `statement_timeout` no PostgreSQL, `socket_timeout` no Redis, `httpx.Timeout` para clientes externos e `--timeout-keep-alive` no uvicorn

### Segurança
- [ ] **HTTP Security Headers** — adicionar middleware com `Strict-Transport-Security`, `X-Frame-Options` e `X-Content-Type-Options`

---

## 📝 Decisões de implementação que divergem do escopo (intencionais)

| Item | Escopo | Implementado | Decisão |
|---|---|---|---|
| Status HMAC inválido | 401 | 400 | **400 correto** — validação de payload, não autenticação |
| Status criação report | 202 | 201 | **201 correto no MVP** — evolui para 202 com Celery |
| Cooldown por IP | 2 min | 2 min (configurável) | Alinhado |
| Penalidade lat/lng redondo | −0.15 | −0.25 | Escopo atualizado para refletir implementação |
| `geo_sig_valid` | Campo no banco | Removido | Campo invariante — sempre `true`, sem valor analítico |
| Recálculo snapshot | Celery task | Background Tasks FastAPI | Bridge para MVP — evolui para Celery na fase de processamento assíncrono |
| Expiração `FOOD_ENDED` | TTL Redis explícito | Remoção implícita por janela de 5 min | Sem Redis no MVP — expira quando ≥3 relatos FOOD_ENDED saem da janela e chega novo relato. Evolui para TTL Redis com Celery |