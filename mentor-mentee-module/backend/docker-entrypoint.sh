#!/bin/sh
set -e
cd /app
alembic upgrade head
# Cloud Run sets PORT (default 8080); local Docker often omits it (see Dockerfile EXPOSE fallback).
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
