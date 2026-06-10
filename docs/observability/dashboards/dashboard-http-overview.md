# Dashboard: HTTP Overview

Documentação do dashboard Grafana de monitoramento HTTP da API Monitoramento RU.
Baseado em métricas coletadas pelo `prometheus-fastapi-instrumentator`.

---

## Sumário

- [Fonte de dados](#fonte-de-dados)
- [Configurações gerais](#configurações-gerais)
- [Variável de filtro](#variável-de-filtro)
- [Linha 1 — Overview](#linha-1--overview)
- [Linha 2 — Tráfego](#linha-2--tráfego)
- [Linha 3 — Qualidade e Erros](#linha-3--qualidade-e-erros)
- [Linha 4 — Latência](#linha-4--latência)
- [Linha 5 — Concorrência](#linha-5--concorrência)
- [Linha 6 — Horários de Pico](#linha-6--horários-de-pico)
- [Referência de métricas do instrumentator](#referência-de-métricas-do-instrumentator)

---

## Fonte de dados

| Campo | Valor |
|---|---|
| Nome | `prometheus-monitor-ru` |
| Tipo | Prometheus |
| UID | `ffomi1nmttds0d` |

Todos os painéis consomem dados desta mesma fonte. As métricas são expostas automaticamente pelo `prometheus-fastapi-instrumentator` no endpoint `/metrics` da aplicação FastAPI.

---

## Configurações gerais

| Configuração | Valor |
|---|---|
| Auto-refresh | 30 segundos |
| Período padrão | Última 1 hora |
| Fuso horário | Navegador do usuário |
| Título | HTTP Overview |
| UID | `ad75qf9` |

---

## Variável de filtro

### `handler` — Filtro por Endpoint

| Campo | Valor |
|---|---|
| Nome interno | `handler` |
| Label exibida | `Endpoint` |
| Descrição | Filtra os painéis por endpoint da API |
| Tipo | Query |
| Query | `label_values(http_requests_total, handler)` |
| Atualização | Ao mudar o intervalo de tempo |
| Multi-valor | Sim |
| Opção "Todos" | Sim |

**Estado atual:** a variável está criada e aparece no topo do dashboard como um dropdown chamado "Endpoint", mas **nenhum painel está utilizando o filtro**. Selecionar um endpoint no dropdown não afeta os gráficos.

### Como aplicar o filtro nos painéis

Para que o dropdown passe a filtrar os dados, é necessário editar as queries dos painéis que possuem o label `handler` e adicionar o seletor `{handler=~"$handler"}`.

**Passo 1** — Identifique os painéis que usam `handler` nas queries. São eles:
- Endpoints Mais Acessados
- Erros por Endpoint
- Latência P95 por Endpoint
- Requisições em Andamento por Endpoint
- Requisições por Segundo por Endpoint (Horários de Pico)

**Passo 2** — Em cada um desses painéis, clique em **Edit** e localize a query no editor.

**Passo 3** — Adicione `{handler=~"$handler"}` à métrica principal. Exemplos:

```promql
-- Antes
topk(10, sum by (handler) (increase(http_requests_total[$__range])))

-- Depois
topk(10, sum by (handler) (increase(http_requests_total{handler=~"$handler"}[$__range])))
```

```promql
-- Antes
histogram_quantile(0.95, sum by (handler, le) (rate(http_request_duration_highr_seconds_bucket[5m])))

-- Depois
histogram_quantile(0.95, sum by (handler, le) (rate(http_request_duration_highr_seconds_bucket{handler=~"$handler"}[5m])))
```

**Por que usar `=~` e não `=`:** com multi-valor ativado, o Grafana gera um valor como `endpoint_a|endpoint_b|endpoint_c`, que é interpretado como expressão regular. Usar `=` causaria erro quando mais de um endpoint estiver selecionado.

---

## Linha 1 — Overview

Quatro painéis do tipo **Stat** posicionados no topo do dashboard. Oferecem uma leitura rápida do estado atual da API sem precisar analisar gráficos.

---

### Total de Requisições

**Tipo:** Stat

**O que representa:** quantidade total de requisições HTTP recebidas pela API desde que o servidor foi iniciado. É um contador cumulativo — só cresce.

**Query:**
```promql
sum(http_requests_total)
```

**Configurações relevantes:**
- Unidade: `short` (número com separador de milhar)
- Cor fixa: azul (informativo, sem threshold de alerta)
- Reduce: último valor não nulo

---

### Requisições por Segundo nos últimos 5min

**Tipo:** Stat

**O que representa:** média de requisições recebidas por segundo calculada sobre uma janela deslizante de 5 minutos. Indica o volume de uso no momento atual.

**Query:**
```promql
sum(rate(http_requests_total[5m]))
```

**Configurações relevantes:**
- Unidade: `reqps` (requisições por segundo)
- Decimais: 2
- Cor fixa: azul (informativo)
- Reduce: último valor não nulo

---

### Taxa de Erros (5xx)

**Tipo:** Stat

**O que representa:** percentual de requisições que resultaram em erro interno do servidor (HTTP 5xx) nos últimos 5 minutos. É o painel mais crítico do dashboard — valores acima de 1% merecem investigação imediata.

**Query:**
```promql
100 * sum(rate(http_requests_total{status="5xx"}[5m]))
/ sum(rate(http_requests_total[5m]))
```

**Configurações relevantes:**
- Unidade: `percent`
- Valor quando sem dados: `0%`
- Decimais: 1
- Thresholds:
  - Verde: 0%
  - Amarelo: 1%
  - Vermelho: 5%

---

### Latência P95

**Tipo:** Stat

**O que representa:** tempo máximo de resposta que 95% das requisições respeitaram nos últimos 5 minutos. Em termos práticos: apenas 1 em cada 20 usuários esperou mais do que esse valor.

**Query:**
```promql
histogram_quantile(0.95,
  sum by (le) (
    rate(http_request_duration_highr_seconds_bucket[5m])
  )
)
```

**Configurações relevantes:**
- Unidade: `s` (segundos — Grafana converte automaticamente para ms quando apropriado)
- Thresholds:
  - Verde: abaixo de 500ms
  - Amarelo: 500ms a 1s
  - Vermelho: acima de 1s

---

## Linha 2 — Tráfego

Três painéis focados em entender como o volume de requisições está distribuído entre métodos HTTP e endpoints.

---

### Requisições por Segundo por Método

**Tipo:** Time series

**O que representa:** evolução do volume de requisições ao longo do tempo, separado por método HTTP (GET, POST, PUT, DELETE, etc). Permite identificar se um pico de tráfego é causado por leituras ou por operações de escrita.

**Query:**
```promql
sum by (method) (rate(http_requests_total[5m]))
```

**Configurações relevantes:**
- Unidade: `reqps`
- Fill opacity: 10 (área suave abaixo das linhas)
- Espessura da linha: 2
- Tooltip: modo single
- Legenda: parte inferior

---

### Distribuição por Método HTTP

**Tipo:** Pie chart (Donut)

**O que representa:** proporção de requisições por método HTTP no período selecionado no time picker do dashboard. Responde à pergunta "qual tipo de operação representa a maior parte do tráfego?".

**Query:**
```promql
sum by (method) (increase(http_requests_total[$__range]))
```

**Observação:** usa `$__range` para se ajustar automaticamente ao período selecionado no time picker — se você estiver visualizando as últimas 6 horas, o pie mostra a distribuição dessas 6 horas.

**Configurações relevantes:**
- Tipo: Donut
- Legenda: exibe valor e percentual
- Ordenação: decrescente

---

### Endpoints Mais Acessados

**Tipo:** Bar chart (horizontal)

**O que representa:** os 10 endereços da API que receberam mais requisições no período selecionado. Indica onde está concentrado o uso da aplicação e quais funcionalidades são mais demandadas.

**Query:**
```promql
topk(10,
  sum by (handler) (
    increase(http_requests_total[$__range])
  )
)
```

**Configurações relevantes:**
- Orientação: horizontal (nomes de endpoints costumam ser longos)
- Unidade: `short`
- Query mode: instant (foto do momento, não série temporal)

---

## Linha 3 — Qualidade e Erros

Quatro painéis dedicados a monitorar a saúde da API através da taxa de erros e da experiência percebida pelos usuários.

---

### Taxa de Erros ao Longo do Tempo

**Tipo:** Time series

**O que representa:** evolução do percentual de erros separado em duas séries — erros do servidor (5xx, em vermelho) e erros do cliente (4xx, em amarelo, como recursos não encontrados ou dados inválidos enviados pelo app). Permite identificar se um problema surgiu de forma gradual ou repentina.

**Queries:**
```promql
-- 5xx (erros do servidor)
100 * sum(rate(http_requests_total{status="5xx"}[5m]))
/ sum(rate(http_requests_total[5m]))

-- 4xx (erros do cliente)
100 * sum(rate(http_requests_total{status="4xx"}[5m]))
/ sum(rate(http_requests_total[5m]))
```

**Configurações relevantes:**
- Unidade: `percent`
- Cores fixas: 5xx = vermelho, 4xx = amarelo
- Fill opacity: 20
- Threshold line em 5% (linha tracejada vermelha no gráfico)
- Mínimo do eixo Y: 0

---

### Erros por Endpoint

**Tipo:** Table

**O que representa:** lista dos endereços da API que geraram erros (4xx ou 5xx) no período selecionado, ordenados da maior para a menor quantidade. Permite identificar rapidamente qual funcionalidade específica está com problema.

**Query:**
```promql
sum by (handler, method, status) (
  increase(http_requests_total{status=~"4xx|5xx"}[$__range])
)
```

**Colunas:**

| Coluna | Descrição |
|---|---|
| Endpoint | Caminho do endpoint da API |
| Método | Método HTTP (GET, POST, etc) |
| Status | Categoria do erro (4xx ou 5xx) com cor de fundo |
| Total de Erros | Quantidade de erros no período |

**Transformações aplicadas:**
1. Labels convertidas em colunas
2. Merge de séries
3. Filtro para exibir apenas as colunas relevantes
4. Ordenação decrescente por total de erros

---

### Apdex Score

**Tipo:** Gauge

**O que representa:** nota de 0 a 1 que resume a qualidade da experiência dos usuários com base na velocidade das respostas. O cálculo considera:
- **Satisfatório:** respostas abaixo de 200ms
- **Tolerável:** respostas entre 200ms e 500ms
- **Frustrante:** respostas acima de 500ms

**Query:**
```promql
(
  sum(rate(http_request_duration_highr_seconds_bucket{le="0.25"}[5m]))
  +
  (
    sum(rate(http_request_duration_highr_seconds_bucket{le="1.0"}[5m]))
    -
    sum(rate(http_request_duration_highr_seconds_bucket{le="0.25"}[5m]))
  ) / 2
)
/
sum(rate(http_request_duration_highr_seconds_count[5m]))
```

**Interpretação:**

| Faixa | Cor | Significado |
|---|---|---|
| 0.85 a 1.0 | Verde | Excelente — usuários satisfeitos |
| 0.70 a 0.84 | Amarelo | Aceitável — degradação perceptível |
| 0.0 a 0.69 | Vermelho | Problemático — usuários insatisfeitos |

**Configurações relevantes:**
- Unidade: `percentunit` (0.0 a 1.0)
- Mínimo: 0, Máximo: 1
- Exibe labels dos thresholds no gauge

---

## Linha 4 — Latência

Dois painéis para análise detalhada do tempo de resposta da API.

---

### Latência Geral (P50 / P95 / P99)

**Tipo:** Time series

**O que representa:** tempo de resposta da API em três perspectivas simultâneas ao longo do tempo. Analisar as três juntas revela padrões que cada uma isolada não mostraria.

**Queries:**
```promql
-- P50: metade das requisições responderam abaixo desse tempo
histogram_quantile(0.50, sum by (le) (rate(http_request_duration_highr_seconds_bucket[5m])))

-- P95: 95% das requisições responderam abaixo desse tempo
histogram_quantile(0.95, sum by (le) (rate(http_request_duration_highr_seconds_bucket[5m])))

-- P99: 99% das requisições responderam abaixo desse tempo
histogram_quantile(0.99, sum by (le) (rate(http_request_duration_highr_seconds_bucket[5m])))
```

**Como interpretar:**

| Situação | O que significa |
|---|---|
| P50 baixo, P99 alto | A maioria é rápida, mas existem picos esporádicos de lentidão |
| P50 e P95 próximos | Latência consistente, sem grandes outliers |
| P95 e P99 crescendo juntos | Degradação generalizada, não apenas casos isolados |
| P99 muito acima do P95 | Requisições específicas estão travando — investigar endpoint por endpoint |

**Configurações relevantes:**
- Unidade: `s`
- Fill opacity: 0 (sem área — três séries com área fica poluído)
- Cores: P50 = azul, P95 = laranja, P99 = vermelho
- Tooltip: modo multi (exibe os três valores ao mesmo tempo no hover)

---

### Latência P95 por Endpoint

**Tipo:** Table

**O que representa:** todos os endpoints ordenados pelo tempo que 95% das suas requisições levaram para responder. Identifica quais funcionalidades específicas estão mais lentas para a maioria dos usuários.

**Query:**
```promql
histogram_quantile(0.95,
  sum by (handler, le) (
    rate(http_request_duration_highr_seconds_bucket[5m])
  )
)
```

**Colunas:**

| Coluna | Descrição |
|---|---|
| Endpoint | Caminho do endpoint |
| P95 Latência | Tempo respondido por 95% das requisições, com cor de fundo |

**Configurações relevantes:**
- Unidade da coluna de latência: `s`
- Decimais: 3
- Cor de fundo da célula por threshold: verde < 500ms, amarelo < 1s, vermelho ≥ 1s
- Ordenação decrescente (endpoints mais lentos no topo)

---

## Linha 5 — Concorrência

Dois painéis para monitorar requisições que estão sendo processadas em tempo real.

> **Pré-requisito:** requer `inprogress_labels=True` na configuração do `Instrumentator`. Sem isso, a métrica `http_requests_inprogress` existe mas não possui os labels `handler` e `method`, tornando o segundo painel inútil.

```python
instrumentator = Instrumentator(
    should_instrument_requests_inprogress=True,
    inprogress_labels=True,  # necessário para o painel por endpoint
)
```

---

### Requisições em Andamento

**Tipo:** Time series

**O que representa:** quantidade de requisições que estão sendo processadas pela API neste exato momento. Útil para detectar acúmulo de requisições presas — um número crescente sem queda indica que a API pode estar travada ou sobrecarregada.

**Query:**
```promql
sum(http_requests_inprogress)
```

**Configurações relevantes:**
- Unidade: `short`
- Fill opacity: 20
- Thresholds como linhas tracejadas: amarelo em 50, vermelho em 100
- Mínimo do eixo Y: -2 (evita que o zero fique colado na borda inferior)

---

### Requisições em Andamento por Endpoint

**Tipo:** Table

**O que representa:** quais endereços da API têm requisições sendo processadas agora. Permite identificar qual funcionalidade específica está retendo conexões abertas.

**Query:**
```promql
sum by (handler, method) (http_requests_inprogress)
```

**Colunas:**

| Coluna | Descrição |
|---|---|
| Endpoint | Caminho do endpoint |
| Método | Método HTTP |
| Em Andamento | Quantidade de requisições ativas, com cor de fundo |

**Observação:** a tabela exibe apenas endpoints com valor maior que zero — quando não há tráfego ativo, a tabela fica vazia intencionalmente.

---

## Linha 6 — Horários de Pico

Dois painéis para identificar padrões de uso ao longo do tempo.

> **Dica:** para visualizar padrões semanais (quais dias da semana têm mais tráfego), ajuste o time picker para **Last 7 days**. Para padrões diários, use **Last 24 hours**.

---

### Volume de Requisições por Hora

**Tipo:** Time series (estilo barras)

**O que representa:** quantidade de requisições agrupadas em janelas de 1 hora. O estilo de barras facilita a comparação visual entre horários — barras mais altas indicam períodos de maior demanda.

**Query:**
```promql
sum(increase(http_requests_total[1h]))
```

**Configurações relevantes:**
- Estilo: barras (`drawStyle: bars`)
- Fill opacity: 80
- Unidade: `short`

---

### Requisições por Segundo por Endpoint

**Tipo:** Time series

**O que representa:** os 5 endpoints mais acessados ao longo do tempo, mostrando como o uso de cada funcionalidade evolui. Permite identificar qual parte da API está causando os picos de tráfego observados no painel anterior.

**Query:**
```promql
topk(5,
  sum by (handler) (
    rate(http_requests_total[5m])
  )
)
```

**Configurações relevantes:**
- Unidade: `reqps`
- Fill opacity: 6
- Legenda exibe: Min, Max e último valor — o **Max** revela o pico histórico de cada endpoint no período visualizado
- Tooltip: modo multi

---

## Referência de métricas do instrumentator

Todas as métricas abaixo são geradas automaticamente pelo `prometheus-fastapi-instrumentator`.

| Métrica | Tipo | Descrição |
|---|---|---|
| `http_requests_total` | Counter | Total de requisições HTTP recebidas. Labels: `handler`, `method`, `status` |
| `http_request_duration_seconds` | Histogram | Duração das requisições em segundos. Labels: `handler`, `method`, `status` |
| `http_requests_inprogress` | Gauge | Requisições sendo processadas no momento. Labels: `handler`, `method` (requer `inprogress_labels=True`) |

### Labels disponíveis

| Label | Valores possíveis | Descrição |
|---|---|---|
| `handler` | `/api/v1/restaurants`, `/api/v1/queue-reports`, etc | Caminho do endpoint (template, não o valor real) |
| `method` | `GET`, `POST`, `PUT`, `DELETE`, `PATCH` | Método HTTP |
| `status` | `2xx`, `4xx`, `5xx` | Categoria do status HTTP (agrupado por `should_group_status_codes=True`) |

### Configuração atual do instrumentator

```python
Instrumentator(
    should_group_status_codes=True,       # agrupa 200/201/204 como "2xx"
    should_ignore_untemplated=True,       # ignora rotas sem template (evita poluição com paths dinâmicos)
    should_respect_env_var=False,         # instrumentação sempre ativa
    should_instrument_requests_inprogress=True,  # habilita a métrica de in-flight
    excluded_handlers=[                   # endpoints excluídos do monitoramento
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
)
```