# 📡 Monitoramento RU — Back-end

<p align="center">
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL"/>
  <img src="https://img.shields.io/badge/Redis-FF4438?style=for-the-badge&logo=redis&logoColor=white" alt="Redis"/>
  <img src="https://img.shields.io/badge/SQLAlchemy-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy"/>
  <img src="https://img.shields.io/badge/Alembic-6DB33F?style=for-the-badge&logo=flask&logoColor=white" alt="Alembic"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker"/>
  <img src="https://img.shields.io/badge/Pytest-0A9EDC?style=for-the-badge&logo=pytest&logoColor=white" alt="Pytest"/>
  <img src="https://img.shields.io/badge/Uvicorn-009688?style=for-the-badge&logo=gunicorn&logoColor=white" alt="Uvicorn"/>
</p>

---

## 📋 Sobre o Projeto

API REST do sistema colaborativo de monitoramento de filas dos Restaurantes Universitários (RU). Usuários enviam relatos da situação da fila pelo front-end; a API valida cada relato por geofence e assinatura HMAC, calcula o status estimado via média ponderada com confidence score, e expõe os snapshots de cada RU para consumo em tempo real.

---

## ✨ Funcionalidades

- ✅ Relatos de fila validados por geofence + HMAC-SHA256 (proteção contra replay attacks)
- ✅ Cálculo de status por média ponderada com janela adaptativa (5/10/15 min)
- ✅ Confidence score por relato com múltiplas penalidades (mock location, GPS impreciso, coordenadas suspeitas)
- ✅ Cooldown por dispositivo (device hash) persistido no banco — evita que uma rede compartilhada (Wi-Fi do campus) bloqueie múltiplos usuários ao mesmo tempo
- ✅ Exceções de horário por restaurante (feriados, horários especiais, fechamentos parciais)
- ✅ Rate limiting via slowapi + Redis — chave por `X-Device-ID` quando presente, com fallback por IP
- ✅ Snapshots de status para almoço e jantar calculados por Background Task após cada relato
- ✅ Endpoint bulk de status para múltiplos RUs em uma única requisição
- ✅ IP e identificador de dispositivo nunca armazenados — apenas hashes SHA-256 (LGPD)
- ✅ Documentação automática via Swagger em `/docs`
- ✅ Debug mode para desenvolvimento sem restrições de horário ou geofence

---

## 🧠 Como funciona o pipeline de relatos

Cada `POST /reports` passa pelas seguintes validações em ordem — a primeira falha interrompe o fluxo:

1. **Restaurante existe e está ativo** → `404` se não encontrado
2. **Geo-assinatura HMAC-SHA256** → `400` se inválida ou expirada (janela padrão: 60s)
3. **Cooldown por dispositivo** → `400` se `X-Device-ID` ausente; `429` se o mesmo dispositivo enviou relato nos últimos 2 minutos
4. **Horário de funcionamento** → `400` se fora do período (exceções têm prioridade sobre schedules regulares)
5. **Geofence** → `400` se as coordenadas excederem o `geofence_radius_m` do restaurante

Após aceitar o relato, uma Background Task recalcula o snapshot com média ponderada:

```
peso_final     = confidence_score × peso_temporal
current_status = Σ(status × peso_final) / Σ(peso_final)
```

| Tempo desde o relato | Peso temporal |
|---|---|
| ≤ 60s | 0.95 |
| ≤ 5 min | 0.70 |
| ≤ 10 min | 0.40 |
| > 10 min | 0.15 |

---

## 🚀 Executando o Projeto

### 🔧 Pré-requisitos

- Docker + Docker Compose
- Python 3.12+ (somente para o modo 1)

### Configuração do `.env`

Crie um arquivo `.env` na raiz do projeto:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=mydb
TEST_DB_NAME=test_db

# Chave para autenticação dos endpoints admin (header X-Admin-Key)
ADMIN_API_KEY=sua-chave-aqui

# Segredo para geração/validação da geo-assinatura HMAC dos relatos
APP_GEO_SECRET=seu-segredo-aqui

# Janela de validade da geo-assinatura em segundos (padrão: 60)
GEO_SIGNATURE_MAX_SKEW_SECONDS=60

# Redis para rate limiting com múltiplos workers
REDIS_URL=redis://localhost:6379

# Origens CORS permitidas (JSON array). Use ["*"] apenas em desenvolvimento.
CORS_ALLOWED_ORIGINS=["http://localhost:5173"]

# Ativa modo debug — NUNCA use true em produção
DEBUG=False

LOG_LEVEL=INFO
LOG_ENV=development
```

---

### Modo 1 — Desenvolvimento local (banco e Redis no Docker, API no host)

Ideal para desenvolvimento com hot-reload nativo e acesso direto ao debugger.

```bash
# 1. Subir apenas banco e Redis
docker compose -f docker/docker-compose.dev.yml up db redis -d

# 2. Instalar dependências
pip install -r requirements.txt -r requirements_dev.txt

# 3. Aplicar migrações
alembic upgrade head

# 4. Iniciar servidor com hot-reload
uvicorn app.main:app --reload --port 8000
```

---

### Modo 2 — Desenvolvimento com Docker (todos os containers)

Sobe a API junto com banco e Redis em containers. Não requer Python instalado localmente.

```bash
# Subir todos os serviços
docker compose -f docker/docker-compose.dev.yml up --build

# Aplicar migrações (primeira vez ou após novas migrations)
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

---

### Modo 3 — Produção

```bash
cd docker

# Build da imagem de produção
docker compose build

# Subir todos os serviços
docker compose up -d

# Aplicar migrações
docker compose exec api alembic upgrade head
```

---

### 🌐 Acesse

- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧪 Testes

```bash
# Todos os testes
pytest

# Com relatório de cobertura
pytest --cov=app --cov-report=html
```

---

## 📦 Endpoints

### Restaurantes

| Método | Path | Auth | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/restaurants` | — | Lista restaurantes ativos |
| `POST` | `/api/v1/restaurants` | Admin Key | Cria restaurante |
| `GET` | `/api/v1/restaurants/{id}` | — | Detalhe do restaurante |
| `PATCH` | `/api/v1/restaurants/{id}` | Admin Key | Atualiza restaurante |

### Horários e Exceções

| Método | Path | Auth | Descrição |
|---|---|---|---|
| `GET` | `/api/v1/restaurants/{id}/schedules` | — | Lista horários de funcionamento |
| `POST` | `/api/v1/restaurants/{id}/schedules` | Admin Key | Cria horário |
| `PATCH` | `/api/v1/restaurants/{id}/schedules/{sid}` | Admin Key | Atualiza horário |
| `GET` | `/api/v1/restaurants/{id}/schedule-exceptions` | — | Lista exceções de horário |
| `GET` | `/api/v1/restaurants/{id}/schedule-exceptions/current` | — | Exceção em vigor agora |
| `POST` | `/api/v1/restaurants/{id}/schedule-exceptions` | Admin Key | Cria exceção |
| `PATCH` | `/api/v1/restaurants/{id}/schedule-exceptions/{eid}` | Admin Key | Atualiza exceção |

### Fila

| Método | Path | Auth | Descrição |
|---|---|---|---|
| `POST` | `/api/v1/restaurants/{id}/reports` | `X-Device-ID` (header) | Envia relato de fila |
| `GET` | `/api/v1/restaurants/{id}/reports/recent` | — | Últimos relatos do período vigente |
| `GET` | `/api/v1/restaurants/{id}/status` | — | Status atual estimado (snapshot) |
| `GET` | `/api/v1/restaurants/status/bulk` | — | Status de múltiplos RUs |

Autenticação admin via header `X-Admin-Key: <ADMIN_API_KEY>`.

---

## 🔒 Rate Limits

A chave do rate limit é determinada na seguinte ordem: **`X-Device-ID`** (header) → **IP** → `"anonymous"`. Endpoints que não recebem `X-Device-ID` usam IP como chave; `POST /reports` usa device, pois o header é obrigatório nesse endpoint.

| Operação | Limite | Chave |
|---|---|---|
| `POST /reports` | 20 req/min | `X-Device-ID` |
| `GET /status` | 60 req/min | IP |
| `GET /status/bulk` | 20 req/min | IP |
| Leitura geral | 60 req/min | IP |
| Escrita admin | 5–20 req/min | IP |

---

## 🐛 Debug Mode

Ativado com `DEBUG=True` no `.env`. **Nunca usar em produção.**

| O que muda | Detalhe |
|---|---|
| `GET /api/v1/debug/geo-signature` exposto | Gera assinaturas válidas para testes no Swagger |
| Janela da geo-assinatura | Ampliada de 60s para 24h |
| `MealPeriodService` | Substituído por `DebugMealPeriodService`: 05h–16h59 = LUNCH, 17h–04h59 = DINNER, sem consultar o banco |
| Geofence | Distância calculada e logada, mas nunca bloqueia o relato |

---

## 📁 Estrutura do Projeto

```
app/
├── api/v1/
│   ├── endpoints/       # Routers por domínio
│   └── router.py
├── core/                # Settings, logging, rate limiter, exception handlers
├── dependencies/        # Injeção de dependências (services, auth)
├── exceptions/          # Exceções de domínio com status HTTP mapeado
├── models/              # SQLAlchemy models (ORM)
├── repositories/        # Queries ao banco
├── schemas/             # Pydantic schemas (request/response)
└── services/            # Regras de negócio
docker/                  # Dockerfile e docker-compose (dev e produção)
docs/                    # Documentação técnica detalhada
scripts/                 # Scripts de inicialização
```

---

## 👨‍💻 Autor

**Kauan Rodrigues Lima**

- GitHub: [Kauanrodrigues01](https://github.com/Kauanrodrigues01)
- LinkedIn: [Kauan Rodrigues](https://www.linkedin.com/in/kauan-rodrigues-lima/)
