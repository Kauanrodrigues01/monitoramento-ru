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
  <img src="https://img.shields.io/badge/Ruff-D7FF64?style=for-the-badge&logo=ruff&logoColor=black" alt="Ruff"/>
  <img src="https://img.shields.io/badge/Bandit-FCA121?style=for-the-badge&logo=python&logoColor=white" alt="Bandit"/>
  <img src="https://img.shields.io/badge/uv-DE5FE9?style=for-the-badge&logo=python&logoColor=white" alt="uv"/>
</p>

---

## 📋 Sobre o Projeto

API REST do sistema colaborativo de monitoramento de filas dos Restaurantes Universitários (RU).

Os usuários enviam relatos da situação da fila pelo aplicativo. A API valida cada relato por geofence e assinatura HMAC, calcula o status estimado utilizando média ponderada com confidence score e disponibiliza snapshots atualizados para consumo em tempo real.

---

## ✨ Funcionalidades

* ✅ Relatos validados por geofence + HMAC-SHA256
* ✅ Proteção contra replay attacks
* ✅ Média ponderada com janela adaptativa (5, 10 e 15 minutos)
* ✅ Confidence score baseado em múltiplos fatores
* ✅ Cooldown por dispositivo persistido no banco
* ✅ Exceções de horário por restaurante
* ✅ Rate limiting distribuído via Redis
* ✅ Snapshots recalculados automaticamente após novos relatos
* ✅ Endpoint bulk para múltiplos restaurantes
* ✅ Conformidade LGPD (IP e Device ID armazenados apenas como hash)
* ✅ Swagger/OpenAPI automático
* ✅ Debug mode para desenvolvimento
* ✅ Gerenciamento moderno de dependências com uv
* ✅ Qualidade automatizada com Ruff, Bandit, Pytest e Pre-Commit
* ✅ Pipeline CI automatizado via GitHub Actions

---

# 🏗️ Arquitetura

O projeto segue uma arquitetura em camadas, separando responsabilidades para facilitar manutenção, testes e evolução.

```text
HTTP Request
      │
      ▼
 FastAPI Endpoint
      │
      ▼
 Service Layer
      │
      ▼
 Repository Layer
      │
      ▼
 PostgreSQL
```

### Camadas

| Camada       | Responsabilidade         |
| ------------ | ------------------------ |
| Endpoints    | Receber requisições HTTP |
| Services     | Regras de negócio        |
| Repositories | Consultas ao banco       |
| Models       | Mapeamento ORM           |
| Schemas      | Validação e serialização |
| Dependencies | Injeção de dependências  |

---

## 🧠 Como funciona o pipeline de relatos

Cada `POST /reports` passa pelas seguintes validações:

1. Restaurante existe e está ativo
2. Geo-assinatura HMAC-SHA256 válida
3. Cooldown por dispositivo
4. Horário de funcionamento
5. Geofence

A primeira validação que falhar interrompe o fluxo.

Após a aceitação do relato, uma Background Task recalcula o snapshot utilizando média ponderada:

```text
peso_final     = confidence_score × peso_temporal

current_status = Σ(status × peso_final) / Σ(peso_final)
```

### Peso temporal

| Tempo desde o relato | Peso |
| -------------------- | ---- |
| ≤ 60s                | 0.95 |
| ≤ 5 min              | 0.70 |
| ≤ 10 min             | 0.40 |
| > 10 min             | 0.15 |

---

# 🚀 Executando o Projeto

## 🔧 Pré-requisitos

### Desenvolvimento Local

* Python 3.14+
* uv
* Docker
* Docker Compose

### Produção

* Docker
* Docker Compose

---

# 📦 Instalando o uv

Linux / macOS:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Verifique:

```bash
uv --version
```

---

# 📥 Clonando o Projeto

```bash
git clone https://github.com/seu-usuario/monitoramento-ru.git

cd back-end-fast-api
```

---

# ⚙️ Configuração do Ambiente

Crie o arquivo `.env`:

```env
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=postgres
DB_NAME=mydb
TEST_DB_NAME=test_db

ADMIN_API_KEY=sua-chave-aqui

APP_GEO_SECRET=seu-segredo-aqui

GEO_SIGNATURE_MAX_SKEW_SECONDS=60

REDIS_URL=redis://localhost:6379

CORS_ALLOWED_ORIGINS=["http://localhost:5173"]

DEBUG=False

LOG_LEVEL=INFO
LOG_ENV=development
```

---

# 📦 Instalando Dependências

O projeto utiliza uv como gerenciador oficial de dependências.

```bash
uv sync --dev
```

---

# 🪝 Instalando os Hooks do Git

Após clonar o projeto, execute:

```bash
uv run pre-commit install
```

Isso instala os hooks locais do Git responsáveis por validar automaticamente o código antes de cada commit.

---

# 🐳 Modo 1 — Desenvolvimento Local

Banco e Redis em containers.

API executando diretamente na máquina.

Subir banco e Redis:

```bash
docker compose -f docker/docker-compose.dev.yml up db redis -d
```

Aplicar migrations:

```bash
uv run alembic upgrade head
```

Executar a API:

```bash
uv run uvicorn app.main:app --reload --port 8000
```

---

# 🐳 Modo 2 — Desenvolvimento com Docker

Todos os serviços executando em containers.

```bash
docker compose -f docker/docker-compose.dev.yml up --build
```

Aplicar migrations:

```bash
docker compose -f docker/docker-compose.dev.yml exec api alembic upgrade head
```

---

# 🐳 Modo 3 — Produção

```bash
cd docker

docker compose build

docker compose up -d
```

Aplicar migrations:

```bash
docker compose exec api alembic upgrade head
```

---

# 🌐 Acesse

Swagger:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

---

# 🧪 Testes

Executar todos os testes:

```bash
uv run pytest
```

Executar com cobertura:

```bash
uv run pytest \
  --cov=app \
  --cov-report=term-missing \
  --cov-report=html
```

---

# 🛠️ Ferramentas Utilizadas

| Ferramenta     | Finalidade                             |
| -------------- | -------------------------------------- |
| uv             | Gerenciamento de dependências          |
| Ruff           | Lint e formatação                      |
| Pytest         | Testes automatizados                   |
| Bandit         | Análise estática de segurança          |
| Pre-Commit     | Validações automáticas antes do commit |
| Docker         | Containers                             |
| GitHub Actions | Integração contínua                    |

---

# 🔍 Qualidade de Código

### Ruff

Formatar:

```bash
uv run ruff format .
```

Lint:

```bash
uv run ruff check .
```

Corrigir automaticamente:

```bash
uv run ruff check . --fix
```

### Bandit

Análise de segurança:

```bash
uv run bandit -r app
```

---

# 🪝 Pre-Commit

Executar manualmente:

```bash
uv run pre-commit run --all-files
```

Os seguintes hooks são executados automaticamente antes de cada commit:

* Ruff Format
* Ruff Check
* Bandit
* Pytest

Fluxo:

```text
git commit
    ↓
ruff format
    ↓
ruff check
    ↓
bandit
    ↓
pytest
    ↓
commit aprovado
```

Se qualquer etapa falhar, o commit é bloqueado.

---

# ⚙️ Integração Contínua (CI)

O GitHub Actions executa automaticamente:

* Ruff Format Check
* Ruff Check
* Pytest
* Coverage

Em:

* Push para `main`
* Push para `develop`
* Pull Requests para `main`
* Pull Requests para `develop`

---

# 🔐 Segurança

Principais mecanismos implementados:

* HMAC-SHA256 para validação dos relatos
* Proteção contra replay attacks
* Geofence para validação de localização
* Rate limiting distribuído via Redis
* Hash SHA-256 para anonimização de IP e Device ID
* Bandit para análise estática de segurança
* Validações automáticas via CI e Pre-Commit
* Containers executados com usuário não privilegiado

---

# 📦 Endpoints

## Restaurantes

| Método | Path                       | Auth      | Descrição                 |
| ------ | -------------------------- | --------- | ------------------------- |
| GET    | `/api/v1/restaurants`      | —         | Lista restaurantes ativos |
| POST   | `/api/v1/restaurants`      | Admin Key | Cria restaurante          |
| GET    | `/api/v1/restaurants/{id}` | —         | Detalhe do restaurante    |
| PATCH  | `/api/v1/restaurants/{id}` | Admin Key | Atualiza restaurante      |

---

## Horários e Exceções

| Método | Path                                                   | Auth      | Descrição        |
| ------ | ------------------------------------------------------ | --------- | ---------------- |
| GET    | `/api/v1/restaurants/{id}/schedules`                   | —         | Lista horários   |
| POST   | `/api/v1/restaurants/{id}/schedules`                   | Admin Key | Cria horário     |
| PATCH  | `/api/v1/restaurants/{id}/schedules/{sid}`             | Admin Key | Atualiza horário |
| GET    | `/api/v1/restaurants/{id}/schedule-exceptions`         | —         | Lista exceções   |
| GET    | `/api/v1/restaurants/{id}/schedule-exceptions/current` | —         | Exceção atual    |
| POST   | `/api/v1/restaurants/{id}/schedule-exceptions`         | Admin Key | Cria exceção     |
| PATCH  | `/api/v1/restaurants/{id}/schedule-exceptions/{eid}`   | Admin Key | Atualiza exceção |

---

## Fila

| Método | Path                                      | Auth        | Descrição            |
| ------ | ----------------------------------------- | ----------- | -------------------- |
| POST   | `/api/v1/restaurants/{id}/reports`        | X-Device-ID | Envia relato         |
| GET    | `/api/v1/restaurants/{id}/reports/recent` | —           | Relatos recentes     |
| GET    | `/api/v1/restaurants/{id}/status`         | —           | Status atual         |
| GET    | `/api/v1/restaurants/status/bulk`         | —           | Status múltiplos RUs |

Autenticação administrativa:

```text
X-Admin-Key: <ADMIN_API_KEY>
```

---

# 🔒 Rate Limits

Ordem da chave:

```text
X-Device-ID → IP → anonymous
```

| Operação      | Limite       |
| ------------- | ------------ |
| POST reports  | 20 req/min   |
| GET status    | 60 req/min   |
| GET bulk      | 20 req/min   |
| Leitura geral | 60 req/min   |
| Escrita admin | 5–20 req/min |

---

# 🐛 Debug Mode

Ativado com:

```env
DEBUG=True
```

Nunca utilize em produção.

### Alterações

* Endpoint de geração de geo-signature habilitado
* Janela da assinatura ampliada para 24 horas
* Geofence nunca bloqueia relatos
* MealPeriodService substituído por implementação de debug

---

# 📁 Estrutura do Projeto

```text
app/
├── api/              # Endpoints FastAPI
├── core/             # Configurações da aplicação
├── dependencies/     # Injeção de dependências
├── exceptions/       # Exceções customizadas
├── models/           # Models SQLAlchemy
├── repositories/     # Acesso ao banco
├── schemas/          # Schemas Pydantic
├── services/         # Regras de negócio

docker/               # Docker e Compose
docs/                 # Documentação técnica
scripts/              # Scripts de inicialização

pyproject.toml
uv.lock
.pre-commit-config.yaml
README.md
```

---

# 🤝 Contribuindo

Após clonar o projeto:

```bash
git clone <repo>

cd back-end-fast-api

uv sync --dev

uv run pre-commit install
```

Antes de abrir um Pull Request:

```bash
uv run pre-commit run --all-files
```

Executar os testes:

```bash
uv run pytest
```

---

# 👨‍💻 Autor

**Kauan Rodrigues Lima**

GitHub:
https://github.com/Kauanrodrigues01

LinkedIn:
https://www.linkedin.com/in/kauan-rodrigues-lima/
