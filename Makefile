.PHONY: install dev api dashboard simulate test lint fmt migrate seed clean \
        up down logs demo check

install:
	uv sync --all-packages --all-extras

api:
	uv run uvicorn app.main:app --reload --host $${GAMEPULSE_API_HOST:-0.0.0.0} --port $${GAMEPULSE_API_PORT:-8000} --app-dir services/api

dashboard:
	uv run streamlit run apps/dashboard/Home.py

simulate:
	uv run python -m simulator --players 25 --duration 120

dev:
	@echo "Run 'make api' and 'make dashboard' in separate shells."

test:
	uv run pytest -q

lint:
	uv run ruff check .
	uv run mypy packages services

fmt:
	uv run ruff format .
	uv run ruff check --fix .

migrate:
	@echo "Apply SQL files in db/migrations to your Supabase project (psql or supabase CLI)."
	@ls db/migrations/*.sql

seed:
	@echo "Apply db/seed.sql to create a demo project + API key."

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f

demo:
	@echo "Starting demo seed (60 players, 5 min)..."
	uv run python scripts/demo_seed.py

check:
	uv run python scripts/check_connectivity.py

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache dist build
