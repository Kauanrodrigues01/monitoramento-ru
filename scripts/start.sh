#!/usr/bin/env sh
set -e

python -m app.core.seed

exec uvicorn app.main:app --host 0.0.0.0 --port 8000
