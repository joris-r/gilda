export DATABASE_URL ?= postgresql+asyncpg://gilda:gilda@localhost:5432/gilda

LITESTAR = uv run --directory backend litestar --app gilda.app:create_app

.DEFAULT_GOAL := help
.PHONY: help install db-up db-down migrate dev dev-backend dev-frontend build \
	test test-backend test-frontend test-e2e lint format check

help: ## List the targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install: ## Install the dependencies of every part
	cd backend && uv sync
	cd frontend && npm install
	cd e2e && npm install && npx playwright install chromium

db-up: ## Start PostgreSQL
	docker compose up -d --wait

db-down: ## Stop PostgreSQL
	docker compose down

migrate: db-up ## Apply the database migrations
	$(LITESTAR) database upgrade --no-prompt

dev: migrate ## Run the backend and the frontend with reload
	$(MAKE) -j2 dev-backend dev-frontend

dev-backend: ## Run the backend with reload, on port 8000
	$(LITESTAR) run --reload

dev-frontend: ## Run the frontend dev server, proxying /api to the backend
	cd frontend && npm run dev

build: ## Type-check and build the frontend
	cd frontend && npm run build

test: test-backend test-frontend test-e2e ## Run every test suite

test-backend: db-up ## Run the backend tests
	cd backend && uv run pytest

test-frontend: ## Run the frontend tests
	cd frontend && npm test

test-e2e: db-up ## Run the end-to-end tests
	cd e2e && npm test

lint: ## Run every quality check, changing nothing
	cd backend && uv run ruff check && uv run ruff format --check && uv run mypy
	cd frontend && npx eslint . && npx prettier --check --experimental-cli src/ && npm run type-check

format: ## Fix lint and formatting where possible
	cd backend && uv run ruff check --fix && uv run ruff format
	cd frontend && npm run lint && npm run format

check: lint test ## Run every quality check and test suite
