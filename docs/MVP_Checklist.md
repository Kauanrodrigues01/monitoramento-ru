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
- [x] Endpoint: `POST` (público)
- [x] Pipeline de validação no `POST`:
  - [x] Restaurant existe e está ativo
  - [x] Assinatura HMAC com `APP_GEO_SECRET` — payload: `{lat:.6f}|{lng:.6f}|{accuracy_m:.1f}|{geo_timestamp}` — retorna `400` se inválida
  - [x] Janela temporal da assinatura: 60s por padrão (`GEO_SIGNATURE_MAX_SKEW_SECONDS` no `.env`)
  - [x] Cooldown por IP: 3 min por padrão (`QUEUE_REPORT_COOLDOWN_MINUTES` no `.env`)
  - [x] Verificação de horário de funcionamento (exceptions → schedules)
  - [x] Geofence (distância vs `geofence_radius_m` do restaurant)
- [x] Campos inferidos pelo servidor: `meal_period`, `ip_hash`, `confidence_score`, `geo_sig_valid`
- [x] Retorna `201` (sem async ainda — evolui para `202` com Celery)

### Confidence Score Service
- [x] `is_mock_location = true` → −0.80
- [x] `accuracy_m` nulo ou 0 → −0.30
- [x] `accuracy_m` entre 20m e 50m → −0.15
- [x] Coordenadas com precisão suspeita (lat/lng redondos) → −0.50
- [x] Score mínimo: 0.05 (floor)
- [ ] IP com histórico de relatos inconsistentes *(pendente — requer dados históricos)*
- [ ] Relato inconsistente com histórico recente do RU *(pendente — requer snapshot funcional)*

---

## 🔲 Pendente — ordenado por prioridade

### 1. Testes unitários pendentes
- [x] `geo_utils.py` e `utils.py` em `core/`
- [x] Schemas de `QueueReport` (verificar cobertura)
- [x] `IpService`
- [x] `ConfidenceScoreService`
- [x] `GeoSignatureService`
- [ ] `QueueReportService`

### 2. Rate limit
- [ ] Adicionar `slowapi` a todos os endpoints da aplicação
- [ ] Regras conforme escopo: 1 req/2min por IP+restaurant para reports, 60 req/min por IP para consultas

### 3. Queue Reports — endpoint de listagem
- [ ] `GET /v1/restaurants/{public_id}/reports/recent` — últimos 20 relatos do período vigente
- [ ] Response: apenas `public_id`, `status`, `meal_period`, `created_at` (nunca expor `ip_hash`, `lat`, `lng`, `confidence_score`)
- [ ] Atualizar/adicionar testes de `QueueReportService` após adição

### 4. Queue Snapshots
- [ ] Model `queue_snapshot`
- [ ] Seed: cada restaurant recebe 2 snapshots (`LUNCH/NO_DATA`, `DINNER/NO_DATA`)
- [ ] Schemas, repository, service
- [ ] Endpoint: `GET /v1/restaurants/{public_id}/status`
- [ ] Possivelmente: criação automática dos snapshots junto com o restaurant (`POST /restaurants`)
- [ ] Testes de schemas
- [ ] Testes de service
- [ ] Testes de integração dos endpoints

### 5. Cálculo de status do snapshot
- [ ] `SnapshotStatusService` com a fórmula:
  ```
  peso_final       = confidence_score × peso_temporal
  status_ponderado = status_value × peso_final
  current_status   = Σ(status_ponderado) / Σ(peso_final)
  ```
  Apenas relatos dentro da janela temporal adaptativa e do `meal_period` vigente.
- [ ] Testes do `SnapshotStatusService`
- [ ] Atualização síncrona do snapshot no `QueueReportService` após criação de report *(evolui para Celery task depois)*

### 6. Testes de integração
- [ ] Endpoints de `restaurants.py`
- [ ] Endpoints de `restaurant_schedules.py`
- [ ] Endpoints de `restaurant_schedule_exceptions.py`
- [ ] Endpoints de `queue_reports.py`
- [ ] Endpoints de `queue_snapshots.py` *(após implementação)*

### 7. Revisões de confidence score
- [ ] Avaliar novas penalidades após snapshot funcional
- [ ] Implementar: IP com histórico de relatos inconsistentes
- [ ] Implementar: Relato inconsistente com histórico recente do RU

---

## 📝 Decisões de implementação que divergem do escopo (intencionais)

| Item | Escopo | Implementado | Decisão |
|---|---|---|---|
| Status HMAC inválido | 401 | 400 | **400 está correto** — é validação de payload, não autenticação |
| Status criação report | 202 | 201 | **201 correto no MVP** — evolui para 202 com Celery |
| Cooldown por IP | 2 min | 2 min (configurável) | Decisão de produto — escopo será atualizado |
| Penalidade lat/lng redondo | −0.15 | −0.25 | Penalidade maior faz sentido — escopo será atualizado |

