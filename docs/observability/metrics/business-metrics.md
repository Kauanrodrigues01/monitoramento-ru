# Business Metrics

Estas métricas representam indicadores de negócio do sistema Monitor RU. Diferentemente das métricas de infraestrutura ou HTTP, elas medem diretamente o comportamento dos usuários e a qualidade dos dados coletados.

---

# queue_reports_created_total

**Tipo:** Counter

**Descrição:** Total de relatos enviados pelos usuários.

Esta métrica é incrementada sempre que um relato é aceito e persistido com sucesso.

## Labels

| Label           | Descrição                     |
| --------------- | ----------------------------- |
| restaurant_id   | Identificador do restaurante  |
| restaurant_name | Nome do restaurante           |
| report_status   | Status informado pelo usuário |

## Valores possíveis de `report_status`

* EMPTY
* SMALL
* MEDIUM
* LARGE
* FULL

## Exemplos de uso

* Restaurantes com maior volume de participação.
* Distribuição dos status informados pelos usuários.
* Volume de relatos ao longo do tempo.

---

# queue_reports_rejected_total

**Tipo:** Counter

**Descrição:** Total de relatos rejeitados pelo sistema.

Permite monitorar problemas de validação, fraude ou uso incorreto da aplicação.

## Labels

| Label           | Descrição                    |
| --------------- | ---------------------------- |
| restaurant_id   | Identificador do restaurante |
| restaurant_name | Nome do restaurante          |
| reason          | Motivo da rejeição           |

## Valores possíveis de `reason`

| Valor                 | Descrição                                  |
| --------------------- | ------------------------------------------ |
| invalid_geo_signature | Assinatura geográfica inválida             |
| expired_geo_signature | Assinatura geográfica expirada             |
| cooldown              | Usuário em período de cooldown             |
| outside_geofence      | Usuário fora da área permitida             |
| outside_meal_hours    | Relato enviado fora do horário da refeição |
| missing_device_id     | Device ID ausente                          |
| other                 | Outros motivos                             |

## Exemplos de uso

* Detectar tentativas de fraude.
* Monitorar problemas de geolocalização.
* Identificar regras de negócio excessivamente restritivas.

---

# queue_reports_confidence_score

**Tipo:** Histogram

**Descrição:** Distribuição do score de confiança calculado para os relatos enviados.

O score varia entre 0 e 1.

Quanto maior o valor, maior a confiabilidade atribuída ao relato.

## Labels

| Label           | Descrição                    |
| --------------- | ---------------------------- |
| restaurant_id   | Identificador do restaurante |
| restaurant_name | Nome do restaurante          |

## Buckets

```text
0.05
0.10
0.20
0.30
0.50
0.70
0.85
0.95
1.00
```

## Exemplos de uso

* Percentil P50, P95 e P99 do score.
* Avaliar qualidade média dos relatos.
* Comparar qualidade dos relatos entre restaurantes.

---

# queue_report_distance_meters

**Tipo:** Histogram

**Descrição:** Distância entre o usuário e o restaurante no momento do envio do relato.

Utilizada para validar presença física e analisar comportamento dos usuários.

## Labels

| Label           | Descrição                         |
| --------------- | --------------------------------- |
| restaurant_id   | Identificador do restaurante      |
| restaurant_name | Nome do restaurante               |
| geofence_result | Resultado da validação geográfica |

## Valores possíveis de `geofence_result`

* inside
* outside

## Buckets

```text
5
10
20
30
40
50
60
70
80
90
100
150
200
```

## Exemplos de uso

* Distância média dos usuários.
* Percentual de usuários próximos ao RU.
* Efetividade da geofence.
* Identificação de possíveis abusos.

---

# rate_limit_blocked_total

**Tipo:** Counter

**Descrição:** Total de requisições bloqueadas por rate limiting.

Ajuda a monitorar abuso da API e comportamento de clientes.

## Labels

| Label    | Descrição          |
| -------- | ------------------ |
| endpoint | Endpoint acessado  |
| method   | Método HTTP        |
| limit    | Limite configurado |

## Exemplos de uso

* Endpoints mais afetados por rate limit.
* Volume de abuso ao longo do tempo.
* Ajuste fino das políticas de limitação.

---

# Recomendações para Dashboards

## Qualidade dos Relatos

* Confidence Score (P50 / P95)
* Distribuição dos Scores
* Distância Média dos Usuários

## Participação dos Usuários

* Total de Relatos por Restaurante
* Relatos por Hora
* Distribuição dos Status Informados

## Segurança e Integridade

* Relatos Rejeitados por Motivo
* Usuários Fora da Geofence
* Bloqueios por Rate Limit

## Ranking de Restaurantes

* Restaurantes com Mais Relatos
* Restaurantes com Maior Taxa de Participação
* Restaurantes com Maior Score Médio de Confiança
