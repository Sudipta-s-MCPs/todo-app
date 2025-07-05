#!/bin/sh
# Startup script for backend
# Created: 2025-01-30 14:50:00 PST

echo "Waiting for database to be ready..."
sleep 5

echo "Running database migrations..."
alembic upgrade head

echo "Initializing database..."
python scripts/init_db.py

echo "Starting FastAPI server..."
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload