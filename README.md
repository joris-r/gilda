# Gilda

A web service for associations to manage their activities. Several
associations share one deployment, each with its own data; each has a
few dozen volunteers. The first feature planned is scheduling
volunteers.

The interface is in English and French.

## Stack

- `backend/`: JSON API in Python (Litestar, Advanced Alchemy,
  PostgreSQL).
- `frontend/`: web interface in Vue 3 and TypeScript.
- `e2e/`: end-to-end tests with Playwright.

## Run

Start PostgreSQL:

```sh
docker compose up -d
export DATABASE_URL=postgresql+asyncpg://gilda:gilda@localhost:5432/gilda
```

Backend:

```sh
cd backend
uv sync
uv run alembic upgrade head
uv run litestar --app gilda.app:create_app run --reload
```

Frontend:

```sh
cd frontend
npm install
npm run dev
```

## Test

```sh
cd backend && uv run pytest
cd frontend && npm test
cd e2e && npm test        # builds the frontend and starts the backend
```

The development process is Dev43: see `spec/`.
