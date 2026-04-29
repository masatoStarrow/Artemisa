#!/bin/bash
set -e

echo "Running Artemisa (Users Service) migrations..."
alembic upgrade head

echo "Starting Artemisa with Uvicorn..."
exec uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1
