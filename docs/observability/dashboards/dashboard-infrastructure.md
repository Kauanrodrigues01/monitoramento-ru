# Infrastructure Dashboard

## Objetivo

O dashboard **Infrastructure** é responsável pelo monitoramento da infraestrutura do servidor onde a aplicação Monitor RU está sendo executada.

Ele fornece uma visão em tempo real sobre utilização de CPU, memória, disco, rede, sistema operacional e processos, permitindo identificar gargalos de infraestrutura antes que impactem os usuários da aplicação.

---

# Origem do Dashboard

Este dashboard é baseado no dashboard oficial da comunidade Grafana:

**Node Exporter Full**

Dashboard ID:

```text
1860
```

Página oficial:

```text
https://grafana.com/grafana/dashboards/1860-node-exporter-full/
```

Autor original:

```text
rfmoz
```

No projeto Monitor RU o dashboard foi importado, provisionado automaticamente pelo Grafana e renomeado para:

```text
Infrastructure
```

---

# Fonte dos Dados

As métricas são coletadas pelo:

```text
Node Exporter
```

e armazenadas pelo:

```text
Prometheus
```

Fluxo:

```text
Servidor Linux
        ↓
Node Exporter
        ↓
Prometheus
        ↓
Grafana
        ↓
Dashboard Infrastructure
```

---

# Configuração do Prometheus

O Prometheus deve possuir um job para o Node Exporter:

```yaml
- job_name: node
  static_configs:
    - targets:
        - host.docker.internal:9100
```

---

# Componentes Necessários

## Node Exporter

Container responsável por coletar métricas do sistema operacional.

Principais métricas coletadas:

* CPU
* Memória
* Disco
* Sistema de arquivos
* Rede
* Load Average
* Processos
* Uptime
* Context Switches
* File Descriptors

---

## Prometheus

Responsável por realizar o scraping das métricas expostas pelo Node Exporter.

---

## Grafana

Responsável pela visualização dos dados através deste dashboard.

---

# Principais Métricas Exibidas

## CPU

Painéis relacionados:

* CPU Usage
* CPU Busy
* CPU System
* CPU User
* CPU IOWait

Permitem identificar:

* Saturação de CPU
* Processos consumindo recursos
* Espera excessiva por I/O

---

## Memória

Painéis relacionados:

* Memory Usage
* Memory Available
* Cached Memory
* Swap Usage

Permitem identificar:

* Consumo excessivo de RAM
* Pressão de memória
* Uso de swap

---

## Disco

Painéis relacionados:

* Disk Usage
* Filesystem Usage
* Disk I/O
* Read/Write Throughput

Permitem identificar:

* Espaço em disco insuficiente
* Gargalos de armazenamento
* Alto volume de leitura/escrita

---

## Rede

Painéis relacionados:

* Network Traffic
* Network Receive
* Network Transmit
* Network Errors

Permitem identificar:

* Consumo de banda
* Picos de tráfego
* Problemas de conectividade

---

## Sistema Operacional

Painéis relacionados:

* Uptime
* Load Average
* Context Switches
* Interrupts

Permitem identificar:

* Sobrecarga do sistema
* Instabilidade
* Reinicializações inesperadas

---

## Processos

Painéis relacionados:

* Total Processes
* Running Processes
* Blocked Processes

Permitem identificar:

* Crescimento anormal de processos
* Processos travados
* Exaustão de recursos

---

# Uso no Monitor RU

Este dashboard complementa os demais dashboards do projeto:

## HTTP Overview

Responsável pelas métricas de aplicação:

* Latência
* Throughput
* Taxa de erros
* Endpoints

## Infrastructure

Responsável pelas métricas de infraestrutura:

* CPU
* Memória
* Disco
* Rede
* Sistema Operacional

Juntos, permitem correlacionar problemas de infraestrutura com degradação da aplicação.

Exemplo:

```text
Latência HTTP aumentou
        ↓
Dashboard Infrastructure mostra CPU em 95%
        ↓
Identificação rápida da causa raiz
```

---

# Provisionamento

Este dashboard é provisionado automaticamente pelo Docker Compose através dos arquivos localizados em:

```text
docker/grafana/dashboards/
```

Dessa forma, não é necessário importá-lo manualmente após subir os containers.

---

# Referências

Grafana Dashboard:

```text
https://grafana.com/grafana/dashboards/1860-node-exporter-full/
```

Node Exporter:

```text
https://github.com/prometheus/node_exporter
```

Prometheus:

```text
https://prometheus.io/
```
