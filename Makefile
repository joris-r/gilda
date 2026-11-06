export DATABASE_URL ?= postgresql+asyncpg://gilda:gilda@localhost:5432/gilda
TEST_DATABASE_URL ?= postgresql+asyncpg://gilda:gilda@localhost:15432/gilda_test
export SMTP_HOST ?= localhost
export SMTP_PORT ?= 11025

LITESTAR = uv run --directory backend litestar --app gilda.app:create_app

.DEFAULT_GOAL := help
.PHONY: help install services-up services-down migrate dev \
	test test-backend test-e2e lint format check

help: ## List the targets
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F ':.*## ' '{printf "  %-14s %s\n", $$1, $$2}'

install: ## Install the dependencies of every part
	cd backend && uv sync
	cd e2e && npm install && npx playwright install chromium

services-up: ## Start PostgreSQL (development and tests) and Mailpit
	docker compose up -d --wait

services-down: ## Stop PostgreSQL (development and tests) and Mailpit
	docker compose down

migrate: services-up ## Apply the database migrations
	$(LITESTAR) database upgrade --no-prompt

dev: migrate ## Run the backend with reload, on port 8000
	$(LITESTAR) run --reload

test: test-backend test-e2e ## Run every test suite

test-backend: export DATABASE_URL = $(TEST_DATABASE_URL)
test-backend: services-up ## Run the backend tests
	cd backend && uv run pytest

test-e2e: export DATABASE_URL = $(TEST_DATABASE_URL)
test-e2e: services-up ## Run the end-to-end tests
	cd e2e && npm test

lint: ## Run every quality check, changing nothing
	cd backend && uv run ruff check && uv run ruff format --check && uv run mypy

format: ## Fix lint and formatting where possible
	cd backend && uv run ruff check --fix && uv run ruff format

check: lint test ## Run every quality check and test suite
