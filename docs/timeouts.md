# Guia de Timeouts — Resiliência da API

Timeout é essencial para evitar que a API fique presa esperando recursos externos e degrade o sistema inteiro.

Sem timeout:
- uma query lenta pode travar conexões do pool;
- Redis lento pode segurar workers;
- poucos requests ruins geram efeito cascata.

```
request → app → banco → serviço externo
         se qualquer um travar, tudo atrás acumula
```

---

## Ordem correta dos timeouts (cascata)

O timeout interno sempre deve ser **menor** que o externo, para que a falha ocorra de dentro para fora:

```
DB query:        5s
App (uvicorn):  30s
Nginx:          35s
Cloudflare:     60s
```

Errado: Nginx = 10s, Uvicorn = 30s → Nginx mata antes, resposta confusa.  
Certo: DB falha primeiro → App responde com erro → Nginx ainda tem margem.

---

## 1. PostgreSQL — `statement_timeout`

Mata queries lentas automaticamente. Configurado via `connect_args` na engine:

```python
# app/core/database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    pool_timeout=5,          # máximo esperando conexão livre do pool
    connect_args={
        "options": "-c statement_timeout=5000"   # 5000ms = 5s por query
    },
)
```

Se a query ultrapassar 5s:
```
ERROR: canceling statement due to statement timeout
```
A API recebe a exception e responde — muito melhor que ficar travada.

**Referências de valor:**
| Operação | Valor sugerido |
|---|---|
| CRUD normal | 3s – 5s |
| Analytics pesado | 10s – 30s |
| Pool timeout | 5s – 10s (não 30s) |

---

## 2. Redis — `socket_timeout`

Se o Redis travar, o request fica preso sem esse parâmetro:

```python
from redis.asyncio import Redis

redis = Redis(
    host="redis",
    port=6379,
    socket_connect_timeout=5,   # timeout para conectar
    socket_timeout=5,            # timeout para operações read/write
)
```

O projeto usa Redis via `REDIS_URL` no slowapi. Ao instanciar o cliente diretamente (ex: para cache futuro), sempre incluir esses dois parâmetros.

---

## 3. HTTP clients externos (httpx)

Se a API vier a chamar serviços externos, usar sempre `httpx.AsyncClient` com timeout explícito:

```python
import httpx

# API externa (ex: serviço de geolocalização)
timeout = httpx.Timeout(
    connect=5.0,    # DNS / TCP / TLS
    read=10.0,      # esperando resposta do servidor
    write=5.0,      # enviando body
    pool=5.0,       # esperando conexão livre do pool
)

async with httpx.AsyncClient(timeout=timeout) as client:
    response = await client.get(url)
```

**Referências rápidas:**
```python
httpx.Timeout(5, read=15)   # API externa
httpx.Timeout(2, read=5)    # microserviço interno
```

Nunca usar `await client.get(url)` sem timeout — um serviço externo lento segura o worker indefinidamente.

---

## 4. Uvicorn

O projeto usa uvicorn diretamente (sem Gunicorn). Configurar `--timeout-keep-alive` para fechar conexões ociosas:

```sh
# scripts/start.sh
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 2 \
  --loop auto \
  --http auto \
  --timeout-keep-alive 5
```

Se evoluir para Gunicorn + UvicornWorker, adicionar `--timeout 30`:

```sh
gunicorn app.main:app \
  -k uvicorn.workers.UvicornWorker \
  -w 4 \
  --timeout 30
```

---

## 5. Nginx (proxy reverso)

```nginx
proxy_connect_timeout  5s;    # conectar no uvicorn
proxy_send_timeout    30s;    # enviar request pro uvicorn
proxy_read_timeout    35s;    # esperar resposta do uvicorn (> app timeout)
send_timeout          30s;    # enviar resposta ao cliente
```

---

## Resumo para este projeto

| Camada | Parâmetro | Valor |
|---|---|---|
| PostgreSQL query | `statement_timeout` | 5000ms |
| PostgreSQL pool | `pool_timeout` | 5s |
| Redis | `socket_timeout` | 5s |
| httpx (externo) | `Timeout(connect=5, read=10)` | — |
| Uvicorn keep-alive | `--timeout-keep-alive` | 5s |
| Gunicorn worker *(futuro)* | `--timeout` | 30s |
| Nginx read | `proxy_read_timeout` | 35s |
