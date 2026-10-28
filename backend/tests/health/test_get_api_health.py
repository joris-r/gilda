from collections.abc import Iterator

import pytest
from litestar.testing import TestClient

from gilda.app import create_app

UNREACHABLE_DATABASE_URL = "postgresql+asyncpg://gilda:gilda@127.0.0.1:1/gilda"


@pytest.fixture
def client() -> Iterator[TestClient]:  # type: ignore[type-arg]
    with TestClient(app=create_app()) as client:
        yield client


@pytest.fixture
def client_without_database(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:  # type: ignore[type-arg]
    monkeypatch.setenv("DATABASE_URL", UNREACHABLE_DATABASE_URL)
    with TestClient(app=create_app()) as client:
        yield client


def test_get_api_health_reports_api_and_database_ok(client: TestClient) -> None:  # type: ignore[type-arg]
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"api": "ok", "database": "ok"}


def test_get_api_health_reports_database_unreachable(
    client_without_database: TestClient,  # type: ignore[type-arg]
) -> None:
    response = client_without_database.get("/api/health")

    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"api": "ok", "database": "unreachable"}
