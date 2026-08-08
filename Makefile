###############################################################################
# OBSIDIAN — Developer Commands
###############################################################################

.PHONY: help setup up down logs backend frontend test lint clean db-migrate

help: ## Show available commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ─────────────────────── Setup ──────────────────────────────────────

setup: ## Initial project setup
	@echo "📦 Setting up OBSIDIAN..."
	cp -n .env.example .env 2>/dev/null || true
	cd backend && python -m venv .venv && .venv/bin/pip install -r requirements.txt
	cd frontend && npm install
	@echo "✅ Setup complete. Edit .env with your API keys."

# ─────────────────────── Docker ─────────────────────────────────────

up: ## Start all services
	docker compose up -d
	@echo "🚀 OBSIDIAN is running"
	@echo "   Frontend:  http://localhost:3000"
	@echo "   Backend:   http://localhost:8000"
	@echo "   Neo4j:     http://localhost:7474"
	@echo "   Qdrant:    http://localhost:6333"

up-infra: ## Start infrastructure only (DB, Redis, Neo4j, Qdrant)
	docker compose up -d postgres redis neo4j qdrant

down: ## Stop all services
	docker compose down

down-clean: ## Stop all services and remove volumes
	docker compose down -v

logs: ## Tail all service logs
	docker compose logs -f

logs-backend: ## Tail backend logs
	docker compose logs -f backend celery-worker

build: ## Build all Docker images
	docker compose build

# ─────────────────────── Development ────────────────────────────────

backend: ## Run backend in development mode
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

celery: ## Run Celery worker
	cd backend && celery -A app.tasks.celery_app worker --loglevel=info

frontend: ## Run frontend in development mode
	cd frontend && npm run dev

# ─────────────────────── Database ───────────────────────────────────

db-migrate: ## Run database migrations
	cd backend && alembic upgrade head

db-revision: ## Create new migration
	cd backend && alembic revision --autogenerate -m "$(msg)"

db-reset: ## Reset database
	cd backend && alembic downgrade base && alembic upgrade head

# ─────────────────────── Testing ────────────────────────────────────

test: ## Run all tests
	cd backend && pytest -v --cov=app
	cd frontend && npm test

test-backend: ## Run backend tests only
	cd backend && pytest -v --cov=app --cov-report=html

test-frontend: ## Run frontend tests only
	cd frontend && npm test

# ─────────────────────── Quality ────────────────────────────────────

lint: ## Run linters
	cd backend && ruff check app/ && mypy app/
	cd frontend && npm run lint

format: ## Format code
	cd backend && ruff format app/
	cd frontend && npx prettier --write src/

# ─────────────────────── Knowledge Base ─────────────────────────────

kb-load: ## Load security knowledge base into Qdrant
	cd backend && python -m app.knowledge.security_kb

kg-init: ## Initialize Neo4j knowledge graph schema
	cd backend && python -m app.knowledge.graph --init

# ─────────────────────── Cleanup ────────────────────────────────────

clean: ## Clean build artifacts
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/htmlcov frontend/.next frontend/out
