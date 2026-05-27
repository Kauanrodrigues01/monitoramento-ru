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
| `GET` (todos os endpoints) | 60 req/min por IP |
| `POST /restaurants` | 10 req/min por IP |
| `PATCH /restaurants/{id}` | 10 req/min por IP |
| `POST /restaurants/{id}/schedules` | 20 req/min por IP |
| `PATCH /restaurants/{id}/schedules/{id}` | 20 req/min por IP |
| `POST /restaurants/{id}/schedule-exceptions` | 5 req/min por IP |
| `PATCH /restaurants/{id}/schedule-exceptions/{id}` | 10 req/min por IP |
| `POST /restaurants/{id}/reports` | 20 req/min por IP (DoS bruto; cooldown real no service) |
| `GET /restaurants/{id}/reports/recent` | 60 req/min por IP |

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

### 1. Revisões de confidence score
- [ ] Avaliar novas penalidades após snapshot funcional
- [ ] Implementar: IP com histórico de relatos inconsistentes
- [ ] Implementar: Relato inconsistente com histórico recente do RU
- [ ] Atualizar testes de service para novas penalidades

### 2. Testes de integração
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