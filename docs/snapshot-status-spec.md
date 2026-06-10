# SIIS — Cálculo de Status do Snapshot
## Especificação Técnica: Implementação Atual vs. Planejado

---

## Visão Geral

O `SnapshotStatusService` é responsável por calcular o `current_status` de um `QueueSnapshot` a partir dos relatos recentes de um RU. O cálculo usa média ponderada com dois fatores: **peso temporal** (quão recente é o relato) e **confidence score** (quão confiável é o relato).

---

## Implementação Atual (MVP)

### Fluxo geral

```
POST /restaurants/{id}/reports
  → QueueReportService persiste o relato
  → Background Task dispara SnapshotStatusService.update_snapshot(ru_id)
      → resolve restaurant + meal_period + relatos dos últimos 15 min
      → _compute_status(recent_reports)
      → persiste novo status no QueueSnapshot
```

### 1. Resolução de contexto (`_resolve_context`)

Executada antes de qualquer cálculo. Realiza 3 queries:

1. Busca o restaurant por `ru_id`
2. Resolve o `meal_period` vigente via `MealPeriodService.resolve(ru_id, at=now)`
3. Busca os relatos dos últimos 15 minutos filtrados por `ru_id` e `meal_period`

O filtro por `meal_period` garante que relatos do almoço não contaminam o cálculo da janta e vice-versa.

---

### 2. Lógica de quórum — `FOOD_ENDED`

Verificada **antes** do cálculo normal. Tem precedência total.

**Condição:** ≥ 3 relatos com `status = FOOD_ENDED` nos últimos **5 minutos**.

```python
_FOOD_ENDED_QUORUM = 3
_FOOD_ENDED_WINDOW_SECONDS = 5 * 60
```

**Se quórum atingido:**
- Retorna `SnapshotStatusEnum.FOOD_ENDED`
- `avg_confidence` = média simples do `confidence_score` dos relatos do quórum
- O cálculo de média ponderada não é executado

**Remoção do `FOOD_ENDED` (comportamento atual — MVP):**

Sem Redis, não há TTL explícito. O `FOOD_ENDED` é removido **implicitamente** quando:
- Os relatos que formaram o quórum saem da janela de 5 minutos, **e**
- Um novo relato chega (disparando o próximo `update_snapshot`)

> **Limitação conhecida:** se nenhum relato chegar após o quórum expirar, o snapshot permanece com `FOOD_ENDED` até a próxima atualização. Ver seção *Planejado* para a solução definitiva.

---

### 3. Janela adaptativa

Calculada sobre os **relatos dos últimos 15 min** (já filtrados por `meal_period`).

| Condição | Janela usada |
|---|---|
| ≥ 5 relatos nos últimos 5 min | 5 minutos |
| ≥ 3 relatos nos últimos 10 min | 10 minutos |
| Demais casos | 15 minutos |

A janela adaptativa se ajusta automaticamente ao volume de atividade: em horários de pico com muitos relatos, usa a janela menor para maior precisão.

---

### 4. Filtragem dos relatos scoráveis

Após determinar a janela, dois filtros são aplicados:

1. **Filtro temporal:** apenas relatos dentro da janela adaptativa
2. **Filtro de status:** exclui `FOOD_ENDED` do cálculo de média (status tratado separadamente no passo 2)

```python
scorable_reports = [r for r in window_reports if r.status in STATUS_MAP_VALUE]
```

**Mapeamento de status para valor numérico:**

| Status | Valor |
|---|---|
| `NO_QUEUE` | 0 |
| `SMALL` | 1 |
| `MEDIUM` | 2 |
| `LARGE` | 3 |

---

### 5. Fórmula de média ponderada

Para cada relato scorável:

```
temporal_weight  = f(seconds_ago)        # ver tabela abaixo
final_weight     = temporal_weight × confidence_score
status_ponderado = status_value × final_weight
```

Acumulando:

```
current_status_value = Σ(status_ponderado) / Σ(final_weight)
current_status       = round(current_status_value) → mapeado para enum
```

**Pesos temporais:**

| Tempo desde o relato | Peso |
|---|---|
| ≤ 60 segundos | 0.95 |
| ≤ 5 minutos | 0.70 |
| ≤ 10 minutos | 0.40 |
| > 10 minutos | 0.15 |

---

### 6. Cálculo do `avg_confidence` persistido

O `confidence_score` salvo no snapshot representa a **confiança média ponderada** dos relatos que formaram o cálculo — não uma média simples.

```python
raw_confidence = total_weight / total_temporal_weight
# onde total_weight     = Σ(temporal_weight × confidence_score)
#       total_temporal_weight = Σ(temporal_weight)
```

Isso significa que relatos mais recentes têm mais influência na confiança média, assim como têm mais influência no status calculado.

---

### 7. Campos atualizados no snapshot

Ao final de `update_snapshot`:

| Campo | Valor |
|---|---|
| `current_status` | Status calculado ou `NO_DATA` |
| `reports_last_15m` | `len(recent_reports)` — sempre conta a janela de 15 min, independente da janela adaptativa usada no cálculo |
| `last_report_at` | `created_at` do relato mais recente, ou `None` se sem relatos |
| `confidence_score` | `avg_confidence` calculado no passo 6 |

---

### 8. Casos especiais

| Situação | Resultado |
|---|---|
| Nenhum relato nos últimos 15 min | `NO_DATA`, `confidence_score = 1.00` |
| Relatos existem mas todos são `FOOD_ENDED` (sem quórum) | `NO_DATA`, `confidence_score = 1.00` |
| `total_weight = 0` (todos confidence_score = 0) | `NO_DATA` — proteção contra divisão por zero (na prática impossível, pois o floor é 0.05) |

---

## Planejado (pós-MVP)

### Expiração explícita do `FOOD_ENDED` via Redis

**Problema atual:** o `FOOD_ENDED` depende de um novo relato para ser removido. Se o RU fechou e ninguém mais envia relatos, o snapshot fica "congelado".

**Solução planejada:**
Quando o quórum for atingido, além de atualizar o snapshot, salvar um override no Redis:

```
chave:  ru:{ru_id}:override:{meal_period}
valor:  { "status": "FOOD_ENDED", "set_at": "..." }
TTL:    min(30 min, segundos até closes_at do slot vigente)
```

No `GET /restaurants/{id}/status`, o backend verifica o Redis antes de retornar o snapshot:
- Se override ativo → retorna `FOOD_ENDED`
- Se override expirado → retorna o status calculado do banco

Isso garante expiração precisa independente de novos relatos chegarem.

---

### Recálculo assíncrono via Celery

**Atual:** Background Tasks do FastAPI — simples mas sem retry, sem persistência de fila, sem monitoramento.

**Planejado:** Celery task `update_snapshot_task(ru_id)` enfileirada após cada report aceito. Vantagens:
- Retry automático em caso de falha
- Visibilidade no dashboard admin
- Retorno do `POST /reports` passa de `201` para `202 Accepted`
- Preparação para a `close_meal_period_task` que reseta o snapshot ao fim de cada período

---

### Penalidades pendentes do `confidence_score`

Duas penalidades definidas no escopo ainda não implementadas — dependem de dados históricos:

| Penalidade | Condição | Valor |
|---|---|---|
| IP com histórico inconsistente | IP que frequentemente diverge do consenso do RU | −0.25 |
| Relato inconsistente com histórico recente | Status muito diferente dos últimos relatos aceitos | −0.20 |

Ambas serão implementadas após `queue_aggregates_10m` estar populado com histórico suficiente.

---

### `close_meal_period_task` — reset do snapshot

Ao encerrar cada período (disparada pelo `sqlalchemy-celery-beat` no `closes_at` do slot):

1. Processar `aggregate_meal_period_task` com os relatos do período
2. Resetar o snapshot: `current_status = NO_DATA`, `last_report_at = None`, `reports_last_15m = 0`, `confidence_score = 1.00`, `override_active = False`
3. Invalidar cache Redis do snapshot
4. Publicar evento WebSocket `RU_CLOSED`

Isso garante que ao abrir o próximo período, o snapshot começa limpo — sem dados do período anterior.

---

## Resumo: Atual vs. Planejado

| Aspecto | MVP atual | Planejado |
|---|---|---|
| Disparo do recálculo | Background Task FastAPI | Celery task com retry |
| Expiração `FOOD_ENDED` | Implícita — janela de 5 min + novo relato | TTL Redis explícito |
| Reset ao fechar período | Não implementado | `close_meal_period_task` |
| Penalidades de histórico | Não implementadas | Após `queue_aggregates_10m` populado |
| Retorno do `POST /reports` | `201 Created` | `202 Accepted` |