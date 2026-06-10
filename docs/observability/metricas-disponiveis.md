# Métricas Disponíveis

## Métricas HTTP (prometheus-fastapi-instrumentator)

### Requisições

```text
http_requests_total
http_requests_created
http_requests_inprogress
```

### Latência

```text
http_request_duration_seconds_bucket
http_request_duration_seconds_count
http_request_duration_seconds_sum
http_request_duration_seconds_created

http_request_duration_highr_seconds_bucket
http_request_duration_highr_seconds_count
http_request_duration_highr_seconds_sum
http_request_duration_highr_seconds_created
```

### Tamanho das Requisições

```text
http_request_size_bytes_count
http_request_size_bytes_sum
http_request_size_bytes_created
```

### Tamanho das Respostas

```text
http_response_size_bytes_count
http_response_size_bytes_sum
http_response_size_bytes_created
```

---

## Métricas de Negócio

### Requisições de Negócio

```text
business_requests_total
business_requests_created
```

### Reports Criados

```text
queue_reports_created_total
queue_reports_created_created
```

### Distância dos Reports

```text
queue_report_distance_meters_bucket
queue_report_distance_meters_count
queue_report_distance_meters_sum
queue_report_distance_meters_created
```

### Score de Confiança dos Reports

```text
queue_reports_confidence_score_bucket
queue_reports_confidence_score_count
queue_reports_confidence_score_sum
queue_reports_confidence_score_created
```

---

## Métricas do Processo Python

### CPU

```text
process_cpu_seconds_total
```

### Memória

```text
process_resident_memory_bytes
process_virtual_memory_bytes
```

### File Descriptors

```text
process_open_fds
process_max_fds
```

### Tempo de Execução

```text
process_start_time_seconds
```

---

## Garbage Collector (GC)

```text
python_gc_collections_total
python_gc_objects_collected_total
python_gc_objects_uncollectable_total
```

---

## Informações do Runtime Python

```text
python_info
```

---

## Métricas Internas do Prometheus

```text
scrape_duration_seconds
scrape_samples_scraped
scrape_samples_post_metric_relabeling
scrape_series_added
```

---

## Resumo

| Categoria | Quantidade |
|------------|------------|
| HTTP | 15 |
| Negócio | 10 |
| Processo Python | 6 |
| Garbage Collector | 3 |
| Runtime Python | 1 |
| Prometheus | 4 |
| **Total** | **39** |

## Observações

### Duas famílias de métricas de latência

Atualmente existem duas famílias de métricas relacionadas ao tempo de resposta:

```text
http_request_duration_seconds_*
http_request_duration_highr_seconds_*
```

Verificar se ambas são necessárias. Caso as duas estejam medindo a mesma informação, pode ser interessante manter apenas uma delas para reduzir cardinalidade e simplificar consultas no Prometheus e Grafana.