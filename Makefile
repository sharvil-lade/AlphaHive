# ============================================================
#  AlphaHive — Developer Makefile
# ============================================================
#
#  Usage:
#    make help          — print this help text
#    make dev           — start infrastructure and run services locally
#    make test          — run the full backend test suite
#    make lint          — run ruff linter over the backend source
#    make build         — build production Docker images
#    make up            — start the full Docker Compose stack
#    make up-monitoring — start stack + Prometheus + Grafana
#    make down          — stop all containers
#    make logs          — tail logs from all running containers
#    make migrate       — apply pending Alembic database migrations
#    make ts-types      — regenerate frontend TypeScript types from Pydantic schemas
#    make clean         — remove Python caches and build artefacts

SHELL := /bin/bash
PYTHON := backend/.venv/Scripts/python
PIP    := backend/.venv/Scripts/pip
PYTEST := $(PYTHON) -m pytest
RUFF   := $(PYTHON) -m ruff

.PHONY: help dev test lint build up up-monitoring down logs migrate ts-types clean

# ── Default target ────────────────────────────────────────────────────────────
help:
	@echo ""
	@echo "  AlphaHive — Makefile targets"
	@echo "  ─────────────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?##' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?##"}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ── Local Development ─────────────────────────────────────────────────────────
dev: ## Start infrastructure containers and run the FastAPI dev server
	docker compose up -d postgres redis qdrant
	@echo "Waiting for services to be healthy..."
	@sleep 5
	$(MAKE) migrate
	PYTHONPATH=backend $(PYTHON) -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run the full backend pytest test suite
	PYTHONPATH=backend $(PYTEST) backend/tests -v

test-ci: ## Run tests in CI mode (no colour, exit on first failure)
	PYTHONPATH=backend $(PYTEST) backend/tests -v --tb=short -x --no-header

# ── Linting ───────────────────────────────────────────────────────────────────
lint: ## Run ruff linter over backend/ source
	$(RUFF) check backend/

lint-fix: ## Auto-fix ruff lint issues
	$(RUFF) check --fix backend/

# ── Docker Compose ────────────────────────────────────────────────────────────
build: ## Build all Docker images
	docker compose build

up: ## Start the full production stack
	docker compose up -d

up-monitoring: ## Start stack + Prometheus + Grafana monitoring
	docker compose --profile monitoring up -d

down: ## Stop and remove all containers
	docker compose --profile monitoring down

logs: ## Tail logs from all running containers
	docker compose logs -f

# ── Database Migrations ───────────────────────────────────────────────────────
# (env.py adds backend/ to sys.path itself, so no PYTHONPATH needed here)
migrate: ## Apply pending Alembic database migrations
	$(PYTHON) -m alembic -c backend/alembic.ini upgrade head

migrate-new: ## Create a new blank Alembic migration (usage: make migrate-new MSG="your message")
	$(PYTHON) -m alembic -c backend/alembic.ini revision --autogenerate -m "$(MSG)"

# ── TypeScript Types ──────────────────────────────────────────────────────────
ts-types: ## Regenerate frontend TypeScript types from Pydantic schemas
	$(PYTHON) backend/scripts/generate_ts_types.py

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Remove Python caches and build artefacts
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	@echo "Clean complete."
