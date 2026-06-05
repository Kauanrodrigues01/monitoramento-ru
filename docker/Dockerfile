# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.14.5-alpine AS builder

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_COMPILE_BYTECODE=0

RUN apk add --no-cache \
    gcc \
    musl-dev \
    linux-headers \
    libffi-dev \
    openssl-dev

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --frozen \
        --no-dev \
        --no-install-project

COPY . .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync \
        --frozen \
        --no-dev

# ── Stage 2: runtime ─────────────────────────────────────────────────────────
FROM python:3.14.5-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN addgroup -S -g 1001 app && \
    adduser -S -u 1001 -G app -H -s /sbin/nologin app

WORKDIR /app

COPY --from=builder /usr/local/lib/python3.14/site-packages/ /usr/local/lib/python3.14/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . .

RUN chmod +x /app/scripts/start.sh && \
    chown -R app:app /app

USER app

EXPOSE 8000

CMD ["/app/scripts/start.sh"]