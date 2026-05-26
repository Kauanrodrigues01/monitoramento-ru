# Validações — POST /api/v1/restaurants/{id}/queue-reports

`create_queue_report` é a função central da aplicação. As validações são executadas em ordem sequencial — qualquer falha interrompe o fluxo imediatamente.

---

## 1. Restaurante existe e está ativo

Busca o restaurante pelo `public_id`. Falha se não existir ou estiver inativo (`is_active=False`).

| Exceção | Status |
|---|---|
| `RestaurantNotFoundError` | 404 |

---

## 2. Assinatura de geolocalização

Garante que o relato veio de um cliente legítimo com acesso à `APP_GEO_SECRET`.

### 2a. Validade do timestamp

Rejeita requisições com `geo_timestamp` fora da janela configurada. Protege contra **replay attacks** — um request interceptado não pode ser resubmetido depois.

- Janela padrão: `GEO_SIGNATURE_MAX_SKEW_SECONDS` (60s)
- Com `DEBUG=True`: 24h (facilita testes locais)

| Exceção | Status |
|---|---|
| `ExpiredGeoSignatureException` | 400 |

### 2b. HMAC-SHA256

Reconstrói o payload canônico e compara com a assinatura recebida em **tempo constante** (`hmac.compare_digest` — evita timing attacks).

Formato do payload:
```
{lat:.6f}|{lng:.6f}|{accuracy_m:.1f}|{geo_timestamp}
```

Quando `accuracy_m` não é informado, o literal `null` é usado no lugar:
```
-3.747360|-38.523060|null|1748166600
```

| Exceção | Status |
|---|---|
| `InvalidGeoSignatureException` | 400 |

---

## 3. Cooldown por IP

Impede que o mesmo IP envie mais de 1 relato bem-sucedido dentro da janela de `QUEUE_REPORT_COOLDOWN_MINUTES` (padrão: 3 min).

- A contagem é feita no banco — funciona com múltiplos workers e sobrevive a restarts
- Conta apenas relatos que chegaram ao commit (relatos rejeitados por outras validações não contam)
- IPs não identificáveis (`"unknown"`) **pulam esta verificação** para não bloquear usuários anônimos entre si

| Exceção | Status |
|---|---|
| `QueueReportTooRecentError` | 429 |

> O `slowapi` (20 req/min) opera em paralelo como proteção contra **DoS bruto**, independente desta lógica.

---

## 4. Horário de funcionamento

Determina o `meal_period` do relato (`LUNCH` ou `DINNER`) seguindo a ordem de prioridade abaixo. A primeira regra que cobrir o horário do relato vence.

### 4a. Exceção CLOSED — dia inteiro

Exceção com `exception_type=CLOSED` e `meal_period=NULL`. Indica que o restaurante está fechado o dia todo. Verificada primeiro porque não depende de saber o período atual.

| Exceção | Status |
|---|---|
| `QueueReportOutsideMealHoursError` | 400 |

### 4b. Exceções CUSTOM_HOURS — horários alternativos

Exceções com `exception_type=CUSTOM_HOURS` substituem o horário regular do restaurante naquele período. Têm `opens_at` e `closes_at` definidos.

Se o timestamp do relato cair dentro de uma dessas janelas, o `meal_period` é inferido a partir da exceção. A consulta aos schedules regulares é **pulada** (evita query desnecessária).

### 4c. Horários regulares — fallback

Consultado apenas se nenhuma `CUSTOM_HOURS` cobriu o horário. Usa os schedules ativos para o dia da semana do relato para inferir o `meal_period`.

### 4d. Nenhum período encontrado

O relato está fora de qualquer janela de funcionamento — seja por ausência de schedules, por `CUSTOM_HOURS` que não cobrem o horário, ou por horário entre períodos.

| Exceção | Status |
|---|---|
| `QueueReportOutsideMealHoursError` | 400 |

### 4e. Exceção CLOSED — período específico

Verificada após descobrir o `meal_period`. Exceções `CLOSED` com `meal_period` definido não têm janela de horário — o match é feito comparando `meal_period` da exceção com o `meal_period` inferido nos passos anteriores.

Exemplo: `CLOSED/LUNCH` bloqueia relatos de almoço, mas **não** bloqueia relatos de jantar.

| Exceção | Status |
|---|---|
| `QueueReportOutsideMealHoursError` | 400 |

> **Por que CLOSED e CUSTOM_HOURS são mutuamente exclusivos?**
> O banco tem um `UniqueConstraint("ru_id", "exception_date", "meal_period")`, então não é possível criar dois registros para o mesmo restaurante, data e período — garantindo que nunca haverá conflito entre os tipos.

---

## 5. Geofence

Calcula a distância haversine entre as coordenadas do relato e as coordenadas cadastradas do restaurante. Rejeita se a distância exceder `geofence_radius_m`.

| Exceção | Status |
|---|---|
| `QueueReportLocationOutOfGeofenceError` | 400 |

---

## Campos calculados pelo servidor

Estes valores **nunca são aceitos do cliente** — são sempre derivados pelo servidor no momento da criação:

| Campo | Como é calculado |
|---|---|
| `meal_period` | Inferido pelo horário do relato via schedules e exceções (passos 4b/4c) |
| `ip_hash` | SHA-256 do IP resolvido — o IP real nunca é armazenado (LGPD) |
| `confidence_score` | Penalidades aplicadas por: mock location (−0.80), accuracy ausente/0 (−0.30), accuracy entre 20–50m (−0.15), coordenadas com arredondamento suspeito (−0.50). Mínimo: 0.05 |
