# ──────────────────────────────────────────────────────────────────────────
# Multi-Agent Research & Report Generation Platform — Convenience Commands
# ──────────────────────────────────────────────────────────────────────────

.PHONY: help up down build logs \
        backend-install backend-dev backend-test backend-lint backend-migrate backend-migration \
        frontend-install frontend-dev frontend-build frontend-lint \
        worker seed clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ── Docker Compose (full stack) ──────────────────────────────────────────

up: ## Start the full stack (Postgres, Redis, ChromaDB, backend, frontend)
	docker compose up --build

down: ## Stop and remove all containers
	docker compose down

build: ## Rebuild all images without starting them
	docker compose build

logs: ## Tail logs from all services
	docker compose logs -f

# ── Backend ───────────────────────────────────────────────────────────────

backend-install: ## Install backend Python dependencies locally
	cd backend && pip install -r requirements.txt --break-system-packages

backend-dev: ## Run the FastAPI backend locally with autoreload
	cd backend && uvicorn main:app --reload

backend-test: ## Run the backend unit test suite with coverage
	cd backend && pytest --cov --cov-report=term-missing --ignore=tests/test_pipeline_integration.py

test-integration: ## Run the integration test against disposable test Postgres (spins up + tears down automatically)
	docker compose -f docker-compose.test.yml up -d --wait
	cd backend && TEST_DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/test_db \
		DATABASE_URL=postgresql+asyncpg://test:test@localhost:5433/test_db \
		pytest tests/test_pipeline_integration.py -v ; \
	docker compose -f docker-compose.test.yml down -v

backend-lint: ## Lint the backend with ruff
	cd backend && ruff check .

backend-migrate: ## Apply all pending Alembic migrations
	cd backend && alembic upgrade head

backend-migration: ## Generate a new Alembic migration (usage: make backend-migration m="add foo")
	cd backend && alembic revision --autogenerate -m "$(m)"

worker: ## Run a local Celery worker
	cd backend && celery -A core.celery_app worker --loglevel=info

# ── Frontend ─────────────────────────────────────────────────────────────

frontend-install: ## Install frontend Node dependencies locally
	cd frontend && npm install

frontend-dev: ## Run the Next.js frontend locally
	cd frontend && npm run dev

frontend-build: ## Production build the frontend
	cd frontend && npm run build

frontend-lint: ## Lint and type-check the frontend
	cd frontend && npm run lint && npm run type-check

# ── Utilities ────────────────────────────────────────────────────────────

seed: ## Populate the local DB with demo research data
	cd backend && python scripts/seed_db.py

clean: ## Remove Python/Node caches and build artifacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.ruff_cache backend/.mypy_cache
	rm -rf frontend/.next frontend/node_modules/.cache
