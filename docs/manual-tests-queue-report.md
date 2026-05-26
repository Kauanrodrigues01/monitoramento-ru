# Testes Manuais — POST /api/v1/restaurants/{id}/queue-reports

## Pré-requisitos

1. Suba a aplicação com `DEBUG=True` no `.env` (ativa o endpoint `/api/v1/debug/geo-signature` e aumenta a janela da assinatura para 24h)
2. Acesse o Swagger em `http://localhost:8000/docs`
3. Tenha em mãos o `public_id` de um restaurante cadastrado com:
   - Coordenadas conhecidas
   - Horário de funcionamento configurado para o período atual (lunch ou dinner)
   - `geofence_radius_m` configurado

### Gerando a assinatura

Use `GET /api/v1/debug/geo-signature` com as coordenadas desejadas antes de cada teste.
Copie `geo_timestamp` e `geo_signature` da resposta.

---

## 1. Happy path — relato criado com sucesso

**Objetivo:** confirmar que um relato válido é criado e retorna 201.

**Request:**
```json
POST /api/v1/restaurants/{public_id}/queue-reports
{
  "status": "SMALL",
  "lat": <lat do restaurante>,
  "lng": <lng do restaurante>,
  "accuracy_m": 12.5,
  "is_mock_location": false,
  "geo_signature": "<assinatura gerada>",
  "geo_timestamp": <timestamp gerado>
}
```

**Esperado:** `201 Created` com `public_id`, `meal_period`, `confidence_score`, etc.

---

## 2. Cooldown — mesmo IP, relato recente

**Objetivo:** confirmar que o segundo relato dentro do cooldown é bloqueado.

**Passos:**
1. Execute o teste 1 com sucesso
2. Gere uma nova assinatura
3. Envie o mesmo request imediatamente

**Esperado:** `429` — "Você já enviou um relato recentemente."

---

## 3. Restaurante não encontrado

**Objetivo:** confirmar erro ao usar um `public_id` inexistente.

**Request:** substitua o `public_id` na URL por um UUID aleatório (ex: `00000000-0000-0000-0000-000000000000`)

**Esperado:** `404` — restaurante não encontrado.

---

## 4. Assinatura geo inválida

**Objetivo:** confirmar que assinatura forjada é rejeitada.

**Request:** use uma `geo_signature` com 64 chars hex aleatórios (ex: `abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890`)

**Esperado:** `400` — "Assinatura de geolocalização é inválida."

---

## 5. Assinatura geo expirada (apenas com `DEBUG=False`)

**Objetivo:** confirmar que timestamp antigo é rejeitado.

**Passos:**
1. Desative `DEBUG` no `.env` e reinicie
2. Use `geo_timestamp` com valor de mais de 60s atrás (ex: `int(time.time()) - 120`)
3. Gere a assinatura correspondente com `GeoSignatureService.build_payload` manualmente

**Esperado:** `400` — "Assinatura de geolocalização expirou."

---

## 6. Fora do geofence

**Objetivo:** confirmar que coordenadas distantes do restaurante são bloqueadas.

**Request:** use coordenadas de outra cidade (ex: `lat: -23.5505, lng: -46.6333` para São Paulo)

**Esperado:** `400` — "Relato enviado muito longe do restaurante."

> **Obs:** a assinatura deve ser gerada com essas coordenadas diferentes.

---

## 7. Fora do horário de funcionamento

**Objetivo:** confirmar bloqueio quando não há schedule ativo para o horário atual.

**Passos:**
1. Remova todos os schedules do restaurante ou configure para um horário que não cobre o momento atual
2. Envie um relato válido

**Esperado:** `400` — "Relato enviado fora do horário de funcionamento."

---

## 8. Exceção de fechamento — dia inteiro

**Objetivo:** confirmar bloqueio quando há uma exceção `CLOSED` sem `meal_period` (dia inteiro).

**Passos:**
1. Crie uma `RestaurantScheduleException` com `exception_type=CLOSED`, `meal_period=null`, `exception_date=hoje`
2. Envie um relato válido

**Esperado:** `400` — "Relato enviado fora do horário de funcionamento."

---

## 9. Exceção de fechamento — período específico

**Objetivo:** confirmar que `CLOSED` para um período específico bloqueia apenas aquele período.

**Passos:**
1. Crie uma exceção `CLOSED` com `meal_period=LUNCH` para hoje
2. Envie um relato no horário de almoço

**Esperado:** `400` — "Relato enviado fora do horário de funcionamento."

3. Envie o mesmo relato no horário de jantar (se houver schedule)

**Esperado:** `201 Created` — jantar não foi bloqueado.

---

## 10. Exceção de horário customizado (`CUSTOM_HOURS`)

**Objetivo:** confirmar que `CUSTOM_HOURS` substitui o horário regular.

**Passos:**
1. Crie uma exceção `CUSTOM_HOURS` com `meal_period=LUNCH`, `opens_at=12:00`, `closes_at=13:00` para hoje
2. Envie um relato com timestamp dentro dessa janela

**Esperado:** `201 Created` com `meal_period=LUNCH`.

3. Envie um relato com timestamp fora dessa janela (ex: 11:50)

**Esperado:** `400` — fora do horário.

---

## 11. Localização simulada (`is_mock_location=true`)

**Objetivo:** confirmar que relato é aceito mas com `confidence_score` reduzido.

**Request:** envie com `is_mock_location: true`

**Esperado:** `201 Created` com `confidence_score < 1.00` (penalidade de 0.80 aplicada).

---

## 12. Sem `accuracy_m`

**Objetivo:** confirmar penalidade de confidence score quando accuracy não é informada.

**Request:** omita o campo `accuracy_m` (ou envie `null`)

> **Obs:** a assinatura deve ser gerada com `accuracy_m=null` no endpoint de debug.

**Esperado:** `201 Created` com `confidence_score` reduzido (penalidade de 0.30).

---

## 13. `accuracy_m` entre 20m e 50m

**Objetivo:** confirmar penalidade intermediária de confidence score.

**Request:** envie `accuracy_m: 35.0`

**Esperado:** `201 Created` com `confidence_score` reduzido (penalidade de 0.15).

---

## 14. Schema inválido — `geo_timestamp` zero ou negativo

**Objetivo:** confirmar validação do Pydantic.

**Requests:**
- `"geo_timestamp": 0`
- `"geo_timestamp": -1`

**Esperado:** `422 Unprocessable Entity` (validação Pydantic, antes de chegar no service).

---

## 15. Schema inválido — `geo_signature` com char não-hex

**Objetivo:** confirmar validação do campo.

**Request:** `"geo_signature": "zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz"`

**Esperado:** `422 Unprocessable Entity`.

---

## 16. Rate limit bruto (slowapi)

**Objetivo:** confirmar que o limite de DoS é aplicado após muitas requisições rápidas.

**Passos:**
1. Envie mais de 20 requisições em menos de 1 minuto (pode usar script ou ferramenta como `hey` ou `wrk`)

**Esperado:** `429` com header `Retry-After` na resposta — mensagem de rate limit do slowapi.

> **Obs:** diferente do cooldown (teste 2), esse 429 vem do `slowapi` e aparece mesmo em requisições com assinatura inválida.
