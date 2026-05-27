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

---

## 🔲 Pendente — ordenado por prioridade

### 1. Testes unitários pendentes
- Nenhum

### 2. Queue Snapshots
- [x] Model `queue_snapshot`
- [x] Seed: cada restaurant recebe 2 snapshots (`LUNCH/NO_DATA`, `DINNER/NO_DATA`)
- [x] Schemas, repository, service
- [x] Endpoint: `GET /v1/restaurants/{public_id}/status`
- [x] Endpoint: `GET /v1/restaurants/status/bulk?ids=uuid1,uuid2,...` (bulk)
- [ ] Possivelmente: criação automática dos snapshots junto com o restaurant (`POST /restaurants`)
- [ ] Testes de schemas
- [ ] Testes de service
- [ ] Testes de integração dos endpoints

### 3. Cálculo de status do snapshot
- [ ] `SnapshotStatusService` com a fórmula:
  ```
  peso_final       = confidence_score × peso_temporal
  status_ponderado = status_value × peso_final
  current_status   = Σ(status_ponderado) / Σ(peso_final)
  ```
  Apenas relatos dentro da janela temporal adaptativa e do `meal_period` vigente.
- [ ] Testes do `SnapshotStatusService`
- [ ] Atualização assincrona do snapshot no `QueueReportService` após criação de report usando Background Tasks do FastAPI *(evolui para Celery task depois)*

### 4. Testes de integração
- [ ] Endpoints de `restaurants.py`
- [ ] Endpoints de `restaurant_schedules.py`
- [ ] Endpoints de `restaurant_schedule_exceptions.py`
- [ ] Endpoints de `queue_reports.py`
- [ ] Endpoints de `queue_snapshots.py` *(após implementação)*

### 5. Revisões de confidence score
- [ ] Avaliar novas penalidades após snapshot funcional
- [ ] Implementar: IP com histórico de relatos inconsistentes
- [ ] Implementar: Relato inconsistente com histórico recente do RU

---

## 🔭 Melhorias futuras (pós-MVP)

### Refactoring
- [ ] **Extrair `_get_restaurant_by_public_id_or_error`** — o método privado já está duplicado em `QueueReportService`, `RestaurantScheduleService` e `RestaurantScheduleExceptionService`, e será repetido em `QueueSnapshotService`. Candidato a um `RestaurantResolverMixin` ou função utilitária em `app/services/_utils.py`, recebendo `restaurant_repo` e `public_id` como parâmetros. O teste isolado em `test_get_restaurant_or_error.py` já cobre o comportamento e pode ser reaproveitado.

### Observabilidade
- [ ] **structlog** — substituir o logger padrão por structlog para logs estruturados em JSON, facilitando ingestão em ferramentas de observabilidade
- [ ] **Prometheus + Grafana** — expor métricas via `prometheus-fastapi-instrumentator` (`/metrics`) e criar dashboards de latência, taxa de erros e volume de relatos por RU

### Resiliência
- [ ] **Timeouts em cascata** — configurar `statement_timeout` no PostgreSQL, `socket_timeout` no Redis, `httpx.Timeout` para clientes externos e `--timeout-keep-alive` no uvicorn. Ver [`docs/timeouts.md`](timeouts.md)

### Segurança
- [ ] **HTTP Security Headers** — adicionar middleware com `Strict-Transport-Security`, `X-Frame-Options` e `X-Content-Type-Options` nas respostas. Ver [`docs/security-headers.md`](security-headers.md)

---

## 📝 Decisões de implementação que divergem do escopo (intencionais)

| Item | Escopo | Implementado | Decisão |
|---|---|---|---|
| Status HMAC inválido | 401 | 400 | **400 correto** — validação de payload, não autenticação |
| Status criação report | 202 | 201 | **201 correto no MVP** — evolui para 202 com Celery |
| Cooldown por IP | 2 min | 2 min (configurável) | Alinhado |
| Penalidade lat/lng redondo | −0.15 | −0.25 | Escopo atualizado para refletir implementação |
| `geo_sig_valid` | Campo no banco | Removido | Campo invariante — sempre `true`, sem valor analítico |