# ── Stage 1: builder ─────────────────────────────────────────────────────────
FROM python:3.12-alpine AS builder

COPY requirements.txt .

RUN apk add --no-cache --virtual .build-deps \
        ca-certificates gcc musl-dev linux-headers libffi-dev openssl-dev && \
    pip install --no-cache-dir -r requirements.txt && \
    find /usr/local \
        \( -type d -a -name test -o -name tests \) \
        -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
        -exec rm -rf '{}' + && \
    runDeps="$( \
        scanelf --needed --nobanner --recursive /usr/local \
                | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
                | sort -u \
                | xargs -r apk info --installed \
                | sort -u \
    )" && \
    apk add --virtual .rundeps $runDeps && \
    apk del .build-deps


# ── Stage 2: final ────────────────────────────────────────────────────────────
FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/

RUN addgroup -S -g 1001 app && \
    adduser -S -u 1001 -G app -H -s /sbin/nologin app

WORKDIR /app

COPY . .

RUN find /usr/local \
        \( -type d -a -name test -o -name tests \) \
        -o \( -type f -a -name '*.pyc' -o -name '*.pyo' \) \
        -exec rm -rf '{}' + && \
    runDeps="$( \
        scanelf --needed --nobanner --recursive /usr/local \
                | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
                | sort -u \
                | xargs -r apk info --installed \
                | sort -u \
    )" && \
    apk add --no-cache --virtual .rundeps $runDeps && \
    chmod +x /app/scripts/start.sh && \
    chown -R app:app /app

EXPOSE 8000

USER app

CMD ["/app/scripts/start.sh"]
