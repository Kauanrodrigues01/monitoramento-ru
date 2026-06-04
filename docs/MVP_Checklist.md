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
  - [x] Cooldown por dispositivo (device_hash): 2 min por padrão (`QUEUE_REPORT_COOLDOWN_MINUTES` no `.env`) — header `X-Device-ID` obrigatório; evita que uma rede compartilhada bloqueie múltiplos usuários ao mesmo tempo
  - [x] Verificação de horário de funcionamento (exceptions → schedules)
  - [x] Geofence (distância vs `geofence_radius_m` do restaurant)
- [x] Campos inferidos pelo servidor: `meal_period`, `ip_hash`, `device_hash`, `confidence_score`
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
- [ ] Divergência com snapshot vigente *(seção 1 do pendente)*
- [ ] IP com histórico de relatos inconsistentes *(pós-MVP — requer `queue_aggregates_10m`)*
- [ ] Relato inconsistente com histórico recente do RU *(pós-MVP — idem)*

### Rate Limit (slowapi)
- [x] Aplicado a todos os endpoints da aplicação
- [x] Chave do rate limit: `X-Device-ID` (header) → IP → `"anonymous"` (implementado em `app/core/rate_limiter.py`)

**Regras definidas** (`app/core/rate_limits.py`):

| Operação | Limite | Chave efetiva |
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
| `POST /restaurants/{id}/reports` | 20 req/min (DoS bruto) | `X-Device-ID` (obrigatório neste endpoint) |
| `GET /restaurants/{id}/reports/recent` | 60 req/min | IP |
| `GET /restaurants/status/bulk` | 20 req/min | IP |
| `GET /restaurants/{id}/status` | 60 req/min | IP |

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
- [ ] `null` quando `current_status` é `NO_DATA` ou `FOOD_ENDED`

#### Migration (Alembic)
- [ ] Gerar migration: `alembic revision --autogenerate -m "add avg_status_value to queue_snapshots"`
- [ ] Verificar migration gerada — confirmar tipo `FLOAT`, `nullable=True`, sem server_default

#### `SnapshotStatusService` (`app/services/snapshot_status_service.py`)
- [ ] Atualizar `_compute_status` para retornar `tuple[SnapshotStatusEnum, Decimal, float | None]`
  - `avg_status_value` = `total_weighted_value / total_weight` (antes do `round`) quando há scorable reports
  - `None` nos paths de `NO_DATA` e `FOOD_ENDED`
- [ ] Atualizar `calculate_snapshot_status` para desempacotar o terceiro elemento com `_`
- [ ] Atualizar `update_snapshot` para persistir `snapshot.avg_status_value = new_avg_status_value`

#### `ConfidenceScoreService` (`app/services/confidence_score_service.py`)
- [ ] Adicionar parâmetro `snapshot: QueueSnapshot | None` ao método de cálculo
- [ ] Implementar penalidade de distância — skip se `snapshot` for `None` ou `snapshot.avg_status_value` for `None`

#### `QueueReportService` (`app/services/queue_report_service.py`)
- [ ] Verificar ordem do pipeline — `meal_period` deve ser inferido **antes** do cálculo do confidence score. Reordenar se necessário:
  `valida geofence → infere meal_period → busca snapshot → calcula confidence_score → persiste`
- [ ] Buscar snapshot via `snapshot_repo.get_by_ru_id_and_meal_period` após inferir `meal_period`
- [ ] Passar snapshot para `ConfidenceScoreService`

#### Schemas
- `avg_status_value` **não será exposto na API** — detalhe de implementação interno. Nenhuma alteração nos schemas.

#### Testes
- [ ] `test_queue_snapshot_model` — verificar constraint `ck_avg_status_value_range`
- [ ] `test_snapshot_status_service.py`:
  - `_compute_status` retorna `avg_status_value` correto (bruto, antes do `round`) com scorable reports
  - `_compute_status` retorna `None` nos paths de `NO_DATA` e `FOOD_ENDED`
  - `update_snapshot` persiste `avg_status_value`
- [ ] `test_confidence_score_service.py`:
  - Penalidade `−0.25` quando distância `≥ 2`
  - Penalidade `−0.15` quando distância `≥ 1.5`
  - Sem penalidade quando `avg_status_value` é `None`
  - Sem penalidade quando snapshot é `None`
- [ ] `test_queue_report_service.py`:
  - Snapshot é buscado após inferência do `meal_period`
  - Snapshot é passado ao `ConfidenceScoreService`
- [ ] Atualizar testes de todas as classes que usam `ConfidenceScoreService` para passar `snapshot` como parâmetro

### 2. Endpoint de exceção de horário vigente

`GET /v1/restaurants/{public_id}/schedule-exceptions/current`

Verifica se existe uma exceção de horário em vigor para o restaurante **hoje** e **no período de refeição corrente** (resolvido pelo `MealPeriodService`). Retorna a exceção encontrada ou `null`.

> **Nota sobre o path:** o segmento é `/current` (não `/active`). "Active" em REST remete a um campo `is_active` de registro; "current" indica o que está em vigor neste momento.

#### Motivação

O frontend precisa saber — antes de exibir o status da fila — se o RU está operando fora do normal hoje. A informação já existe na tabela `restaurant_schedule_exceptions`, mas o endpoint atual (`GET /schedule-exceptions`) retorna todas as exceções cadastradas, exigindo filtragem no cliente.

#### Contrato de resposta

| Cenário | HTTP | Body |
|---|---|---|
| Exceção encontrada | 200 | objeto `ScheduleExceptionResponse` |
| Nenhuma exceção hoje | 200 | `{ "exception": null }` |
| Restaurante não encontrado | 404 | `ErrorResponse` |
| Fora do horário de funcionamento | 200 | `{ "exception": null }` (sem período vigente, sem exceção aplicável) |

**Exemplo — restaurante fechado o dia todo:**
```json
{
  "exception": {
    "public_id": "...",
    "exception_type": "CLOSED",
    "exception_date": "2026-06-12",
    "meal_period": null,
    "opens_at": null,
    "closes_at": null,
    "reason": "Feriado de Corpus Christi"
  }
}
```

**Exemplo — horário especial no almoço:**
```json
{
  "exception": {
    "public_id": "...",
    "exception_type": "CUSTOM_HOURS",
    "exception_date": "2026-06-12",
    "meal_period": "LUNCH",
    "opens_at": "11:30:00",
    "closes_at": "13:00:00",
    "reason": null
  }
}
```

**Exemplo — sem exceção:**
```json
{ "exception": null }
```

#### Implementação

- **Schema novo:** `ScheduleExceptionActiveResponse` com campo `exception: ScheduleExceptionResponse | None`
- **Repositório** (`RestaurantScheduleExceptionRepository`): `get_by_ru_id_and_date` já existe — reutilizar; filtrar pelo `meal_period` resolvido no service
- **Service** (`RestaurantScheduleExceptionService`): método `get_active_exception(ru_id, at)` que:
  1. Chama `list_by_ru_id_and_date(ru_id, at.date())`
  2. Prioriza exceção `CLOSED` sem `meal_period` (dia inteiro)
  3. Depois procura `CLOSED` ou `CUSTOM_HOURS` com o `meal_period` resolvido pelo `MealPeriodService`
  4. Se `MealPeriodService` lançar `OutsideMealHoursError` / `RestaurantClosedAllDayError` — retorna `None`
- **Router** (`restaurant_schedule_exceptions.py`): `GET /{public_id}/schedule-exceptions/current` público, rate limit 60 req/min

#### Testes
- [x] Retorna exceção `CLOSED` sem `meal_period` quando o dia inteiro está fechado
- [x] Retorna exceção `CUSTOM_HOURS` para o período correto
- [x] Retorna `null` quando não há exceção para hoje
- [x] Retorna `null` quando o horário atual não corresponde a nenhum período de refeição
- [x] Retorna `404` quando o restaurante não existe

---

### 3. Endpoint de métricas gerais (`/metrics/summary`)

`GET /v1/metrics/summary`

Visão agregada do sistema em tempo real. Voltado para o painel principal do front-end.

#### Contrato de resposta

```json
{
  "total_active_restaurants": 3,
  "open_now": 2,
  "reports_last_15m": 14,
  "status_distribution": {
    "NO_QUEUE": 1,
    "SMALL": 1,
    "MEDIUM": 0,
    "LARGE": 0,
    "FOOD_ENDED": 0,
    "NO_DATA": 1
  },
  "avg_confidence": 0.87
}
```

| Campo | Origem |
|---|---|
| `total_active_restaurants` | `COUNT` de `restaurants` com `is_active=true` |
| `open_now` | Agregação dos snapshots com `meal_period` vigente (reusa lógica do `MealPeriodService`) |
| `reports_last_15m` | `SUM(reports_last_15m)` dos snapshots do período vigente |
| `status_distribution` | `COUNT GROUP BY current_status` dos snapshots do período vigente |
| `avg_confidence` | Média de `confidence_score` dos snapshots com `current_status != NO_DATA` |

#### Implementação

- **Schema:** `MetricsSummaryResponse`
- **Service:** `MetricsService.get_summary()` — queries diretas ao banco via `QueueSnapshotRepository` e `RestaurantRepository`; sem cache no MVP
- **Router:** `GET /v1/metrics/summary` — público, rate limit 30 req/min
- Não requer autenticação — todos os valores são agregados, sem dados individuais

#### Testes
- [ ] Contagem correta de restaurantes ativos
- [ ] `open_now` considera apenas restaurantes com período vigente no momento
- [ ] `reports_last_15m` soma todos os snapshots do período vigente
- [ ] `status_distribution` agrupa corretamente os status
- [ ] `avg_confidence` exclui snapshots com `NO_DATA`

---

### 4. Endpoint de métricas por restaurante

`GET /v1/restaurants/{public_id}/metrics`

Dados de atividade do restaurante **no dia corrente**, para exibição na página de detalhe. Permite mostrar como a fila evoluiu ao longo do dia.

#### Contrato de resposta

```json
{
  "reports_today": 42,
  "avg_confidence_today": 0.83,
  "status_history_today": [
    { "hour": 11, "meal_period": "LUNCH",  "dominant_status": "SMALL",  "report_count": 5 },
    { "hour": 12, "meal_period": "LUNCH",  "dominant_status": "LARGE",  "report_count": 12 },
    { "hour": 13, "meal_period": "LUNCH",  "dominant_status": "MEDIUM", "report_count": 8 },
    { "hour": 17, "meal_period": "DINNER", "dominant_status": "SMALL",  "report_count": 3 }
  ]
}
```

| Campo | Origem |
|---|---|
| `reports_today` | `COUNT` de `queue_reports` com `ru_id` e `created_at` no dia atual (timezone local) |
| `avg_confidence_today` | Média de `confidence_score` dos relatos de hoje |
| `status_history_today` | Relatos de hoje agrupados por hora; `dominant_status` = status com maior peso ponderado por confidence na hora |

> `status_history_today` é a base para um gráfico de linha ou sparkline no frontend mostrando a evolução da fila durante o dia.

#### Implementação

- **Schema:** `RestaurantMetricsResponse`, `StatusHistoryEntry`
- **Repositório** (`QueueReportRepository`): `list_today_by_ru` — query com `created_at BETWEEN day_start AND day_end` (usando `ZoneInfo(APP_TIMEZONE)`, igual ao `list_recent_by_period` já implementado)
- **Service:** `MetricsService.get_restaurant_metrics(ru_id, day)` — agrupa os relatos por hora em Python; `dominant_status` calculado como moda ponderada por `confidence_score`
- **Router:** `GET /v1/restaurants/{public_id}/metrics` — público, rate limit 30 req/min
- Retorna `404` se restaurante não existir; retorna métricas zeradas/vazias se não houver relatos hoje (não é erro)

#### Testes
- [ ] `reports_today` conta apenas relatos do dia corrente no timezone da aplicação (não UTC)
- [ ] `avg_confidence_today` é `null` quando não há relatos hoje
- [ ] `status_history_today` está vazio quando não há relatos
- [ ] `dominant_status` por hora é o status com maior soma de `confidence_score` na hora
- [ ] Retorna `404` quando o restaurante não existe

---

### 5. Refactoring
- [ ] **Extrair `_get_restaurant_by_public_id_or_error`** — método privado duplicado em `QueueReportService`, `RestaurantScheduleService`, `RestaurantScheduleExceptionService` e `QueueSnapshotService`. Candidato a `RestaurantResolverMixin` ou função utilitária em `app/services/_utils.py`. Teste isolado em `test_get_restaurant_or_error.py` já cobre o comportamento.
- [ ] Atualizar testes necessários após refatoração

### 3. WebSocket — status em tempo real
- [ ] Endpoint `WS /v1/ws/restaurants/{public_id}/status?token=...`
- [ ] Ao conectar: enviar snapshot atual imediatamente
- [ ] A cada recálculo de snapshot (Background Task): publicar novo snapshot para todos os clientes conectados no RU
- [ ] Se RU estiver fechado no momento da conexão: retornar código de fechamento `4000` com mensagem `RU_CLOSED`
- [ ] Contrato de reconexão (documentado para o cliente): backoff exponencial — 1s, 2s, 4s, 8s, 16s, máx 30s; após 5 tentativas sem sucesso exibir aviso de conectividade
- [ ] Rate limit: 1 conexão simultânea por IP por RU
- [ ] Testes do endpoint WebSocket

### 4. Testes de integração
- [ ] Endpoints de `restaurants.py`
- [ ] Endpoints de `restaurant_schedules.py`
- [ ] Endpoints de `restaurant_schedule_exceptions.py`
- [ ] Endpoints de `queue_reports.py`
- [ ] Endpoints de `queue_snapshots.py`

---

## 🔭 Melhorias futuras (pós-MVP)

### Observabilidade
- [ ] **structlog** — substituir logger padrão por structlog para logs estruturados em JSON
- [ ] **Prometheus + Grafana** — expor métricas via `prometheus-fastapi-instrumentator` (`/metrics`) e criar dashboards de latência, taxa de erros e volume de relatos por RU

### Processamento assíncrono

> **Broker:** RabbitMQ (em vez de Redis). Vantagens sobre Redis como broker: persistência de mensagens em disco por padrão (tasks sobrevivem a crashes de workers), Dead Letter Queue nativa para tasks que esgotaram retries, Management UI com visibilidade de filas em tempo real. Redis permanece exclusivamente para cache (snapshots, schedules, rate limit).

#### Infraestrutura
- [ ] Adicionar serviço `rabbitmq` ao Docker Compose (`rabbitmq:3-management`) com Management UI na porta 15672
- [ ] Configurar Celery com `broker_url = amqp://...` e `result_backend = redis://...`
- [ ] Substituir Background Tasks do FastAPI por Celery task `update_snapshot_task(ru_id)`. Retorno do `POST /reports` passa de `201` para `202 Accepted`
- [ ] **sqlalchemy-celery-beat** — scheduler dinâmico com schedules persistidos no PostgreSQL para tasks com horário variável (baseadas em `restaurant_schedules`)

#### `queue_aggregates_10m` — model e infraestrutura
- [ ] Model `queue_aggregate_10m` com campos: `ru_id`, `meal_period`, `weekday`, `bucket_start`, `bucket_end`, `avg_status`, `avg_confidence`, `report_count`, `food_ended_count`
  - PK composta: `(ru_id, meal_period, bucket_start)`
  - `bucket_start` sempre múltiplo de 10 min do grid global (00:00, 00:10 ... 23:50)
  - `weekday` extraído de `bucket_start` via `EXTRACT(DOW FROM bucket_start)` na task
  - Índice adicional: `(ru_id, weekday, meal_period)` para queries de heatmap
- [ ] Repository: `upsert_bucket`, `list_by_ru_and_period`, `list_for_heatmap`
- [ ] Schemas de response para endpoint de previsão
- [ ] Testes do model e repository

#### Tasks assíncronas
- [ ] **`close_meal_period_task(ru_id, meal_period, opens_at, closes_at)`** — disparada pelo beat no `closes_at` de cada slot:
  1. Verifica se houve relatos no período
  2. Se sim: enfileira `aggregate_meal_period_task`
  3. Reseta snapshot: `current_status=NO_DATA`, `last_report_at=None`, `reports_last_15m=0`, `confidence_score=1.00`, `avg_status_value=None`
  4. Invalida cache Redis do snapshot
  5. Publica evento WebSocket `RU_CLOSED` para clientes conectados
- [ ] **`aggregate_meal_period_task(ru_id, meal_period, opens_at, closes_at)`** — processa relatos do período encerrado em buckets fixos de 10 min e grava em `queue_aggregates_10m`
- [ ] **`FOOD_ENDED` override via Redis** — substituir remoção implícita por janela por TTL explícito no Redis: `min(30 min, tempo restante até closes_at)`. Garante expiração precisa independente de novos relatos chegarem
- [ ] **`sync_scheduled_tasks(ru_id, target_date)`** — chamada no startup e a cada alteração de `restaurant_schedules` ou `restaurant_schedule_exceptions`: cria/atualiza `PeriodicTask` com `ClockedSchedule` apontando para o `closes_at` de cada slot
- [ ] Testes das tasks

#### Job 2 — Cache semanal (CrontabSchedule, domingos às 02:00)
- [ ] Lê `queue_aggregates_10m` agrupando por `ru_id`, `weekday`, `meal_period`
- [ ] Aplica `normalize_for_query(opens_at, closes_at, bucket_size=10)` para filtrar buckets dentro do schedule vigente
- [ ] Calcula médias de `avg_status` e `report_count` por slot
- [ ] Salva no Redis: `analytics:ru:{id}:weekly` com TTL de 7 dias
- [ ] Endpoint `GET /v1/restaurants/{public_id}/prediction` — retorna previsão histórica filtrada pelo schedule atual

#### Job 3 — Limpeza de dados *(em avaliação)*
- [ ] Política de retenção a definir: 90 dias para `queue_reports`, 365 dias para `queue_aggregates_10m` e `admin_audit_log`
- [ ] Avaliar se a limpeza será via CrontabSchedule (Celery), pg_cron, ou script de manutenção manual

### Confidence score — penalidades históricas
- [ ] **IP com histórico inconsistente** — requer `queue_aggregates_10m` populado com histórico suficiente
- [ ] **Relato inconsistente com histórico recente do RU** — idem

### Resiliência
- [ ] **Timeouts em cascata** — `statement_timeout` no PostgreSQL, `socket_timeout` no Redis, `httpx.Timeout` para clientes externos, `--timeout-keep-alive` no uvicorn

### Segurança
- [ ] **HTTP Security Headers** — `Strict-Transport-Security`, `X-Frame-Options`, `X-Content-Type-Options`

---

## 📝 Decisões de implementação que divergem do escopo (intencionais)

| Item | Escopo | Implementado | Decisão |
|---|---|---|---|
| Status HMAC inválido | 401 | 400 | **400 correto** — validação de payload, não autenticação |
| Status criação report | 202 | 201 | **201 correto no MVP** — evolui para 202 com Celery |
| Cooldown por dispositivo (device_hash) | 2 min | 2 min (configurável) | Migrado de IP para device_hash — evita bloqueio em redes compartilhadas |
| Penalidade lat/lng redondo | −0.15 | −0.25 | Escopo atualizado para refletir implementação |
| `geo_sig_valid` | Campo no banco | Removido | Campo invariante — sempre `true`, sem valor analítico |
| Recálculo snapshot | Celery task | Background Tasks FastAPI | Bridge para MVP — evolui para Celery na fase de processamento assíncrono |
| Expiração `FOOD_ENDED` | TTL Redis explícito | Remoção implícita por janela de 5 min | Sem Redis no MVP — expira quando ≥3 relatos FOOD_ENDED saem da janela e chega novo relato |
| Broker Celery | Redis | RabbitMQ | RabbitMQ para tasks (persistência, DLQ, visibilidade); Redis exclusivo para cache |