# Debug Mode

Ativado via variável de ambiente:

```env
DEBUG=true
```

Padrão: `False`. **Nunca ativar em produção** — desativa validações de segurança e expõe endpoints sensíveis.

---

## O que muda quando `DEBUG=True`

### 1. Endpoints de debug expostos

O router `/api/v1/debug` é registrado somente quando `DEBUG=True`.

| Endpoint | Descrição |
|---|---|
| `GET /debug/ip` | Retorna o IP do cliente e todos os headers de proxy (`CF-Connecting-IP`, `X-Forwarded-For`, `X-Real-IP`). Útil para verificar se o IP está sendo lido corretamente atrás de proxies. |
| `GET /debug/geo-signature` | Gera um `geo_signature` válido a partir de `lat`, `lng` e `accuracy_m`. Permite testar envio de `queue_reports` sem precisar de um cliente mobile. |

---

### 2. Janela de validade da geo-signature ampliada

Em produção, a geo-signature expira em `GEO_SIGNATURE_MAX_SKEW_SECONDS` (padrão: **60 segundos**).

Com `DEBUG=True`, a janela passa para **86400 segundos (24 horas)**, permitindo reutilizar uma assinatura gerada manualmente durante testes sem precisar regenerá-la a cada minuto.

Arquivo: `app/services/geo_signature_service.py`

---

### 3. MealPeriodService substituído por DebugMealPeriodService

Em produção, o período de refeição ativo é resolvido consultando os schedules e exceções cadastrados no banco para o restaurante.

Com `DEBUG=True`, o `DebugMealPeriodService` é injetado no lugar — sem nenhuma consulta ao banco. A resolução é feita apenas pelo horário atual:

| Horário | Período |
|---|---|
| 05:00 – 16:59 | `LUNCH` |
| 17:00 – 04:59 | `DINNER` |

Isso significa que `GET /restaurants/{id}/status` e `POST /restaurants/{id}/reports` funcionam sem nenhum schedule cadastrado.

Arquivo: `app/services/debug_meal_period_service.py`  
Injetado em: `app/dependencies/meal_period_dependencies.py`

---

### 4. Validação de geofence ignorada

Em produção, o relato é rejeitado com `400` se a distância entre as coordenadas enviadas e o restaurante exceder `geofence_radius_m`.

Com `DEBUG=True`, a distância ainda é calculada (e logada em `DEBUG`), mas a exceção `QueueReportLocationOutOfGeofenceError` nunca é levantada — o relato passa independente da distância.

Útil para testar envios a partir de máquinas fora do campus sem precisar falsificar coordenadas.

Arquivo: `app/services/queue_report_service.py`
