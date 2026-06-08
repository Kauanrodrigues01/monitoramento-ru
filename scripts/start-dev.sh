#!/usr/bin/env sh
set -e

export PYTHONPATH="/app/app"

alembic upgrade head

python -m app.core.seed

python -m app.core.seed_dev

exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --loop auto --http auto --reload
