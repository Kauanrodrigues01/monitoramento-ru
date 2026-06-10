# Instrumentação Prometheus

## Objetivo

A aplicação utiliza a biblioteca `prometheus-fastapi-instrumentator` para expor métricas HTTP compatíveis com Prometheus através do endpoint `/metrics`.

Essas métricas são utilizadas pelos dashboards do Grafana para monitoramento de tráfego, latência, erros e disponibilidade da API.

---

## Configuração

```python
Instrumentator(
    should_group_status_codes=True,
    should_ignore_untemplated=True,
    should_respect_env_var=False,
    should_instrument_requests_inprogress=True,
    inprogress_labels=True,
    excluded_handlers=[
        r"^/metrics$",
        r"^/docs$",
        r"^/redoc$",
        r"^/openapi\.json$",
        r"^/health.*",
        r"^.*/debug.*",
        r"^.*/ws.*",
    ],
)
```

---

## Opções Utilizadas

### should_group_status_codes=True

Agrupa códigos HTTP por categoria:

* 2xx
* 3xx
* 4xx
* 5xx

Exemplo:

```text
status="2xx"
```

---

### should_ignore_untemplated=True

Agrupa rotas utilizando o template definido pelo FastAPI.

Exemplo:

```text
/api/v1/restaurants/{restaurant_id}
```

Em vez de:

```text
/api/v1/restaurants/1
/api/v1/restaurants/2
/api/v1/restaurants/3
```

Reduz drasticamente a cardinalidade das métricas.

---

### should_instrument_requests_inprogress=True

Cria a métrica:

```text
http_requests_inprogress
```

Representa a quantidade de requisições sendo processadas naquele momento.

---

### inprogress_labels=True

Adiciona labels de método HTTP à métrica de requisições em andamento.

Exemplo:

```text
http_requests_inprogress{method="GET"}
```

---

## Endpoints Excluídos

### Métricas

```text
/metrics
```

Evita que o próprio Prometheus gere tráfego artificial nas métricas.

---

### Documentação

```text
/docs
/redoc
/openapi.json
```

Evita que acessos ao Swagger e OpenAPI poluam os dashboards.

---

### Health Checks

```text
/health/*
```

Health checks são executados frequentemente por load balancers, Kubernetes e sistemas de monitoramento.

Incluí-los distorceria métricas de tráfego real da aplicação.

---

### Endpoints Debug

```text
*/debug*
```

Rotas de depuração não representam uso real do sistema.

---

### WebSockets

```text
*/ws*
```

Conexões WebSocket não representam requisições HTTP tradicionais.

Sua inclusão causaria distorções em:

* taxa de requisições
* latência
* endpoints mais acessados
* Apdex

---

## Endpoint de Métricas

```text
GET /metrics
```

Retorna todas as métricas Prometheus da aplicação.

Esse endpoint é consumido exclusivamente pelo Prometheus.

---

## Dashboards Relacionados

* HTTP Overview
* Infrastructure (Node Exporter)
* Business Metrics

---

## Observações

O endpoint:

```text
/api/v1/metrics/summary
```

não é excluído da instrumentação.

A regex utilizada para excluir `/metrics` é:

```python
r"^/metrics$"
```

Portanto apenas o endpoint raiz `/metrics` é ignorado.
