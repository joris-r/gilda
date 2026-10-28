import uuid
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from litestar.testing import TestClient

from gilda.app import create_app

PASSWORD = "correct horse"


def unique_email(name: str) -> str:
    """Each test uses fresh emails, so tests never see each other's users."""
    return f"{name.lower()}-{uuid.uuid4().hex[:12]}@example.org"


@pytest.fixture
def new_client() -> Iterator[Callable[[], Any]]:
    """Opens extra clients, each with its own cookies (its own browser)."""
    opened: list[Any] = []

    def open_client() -> Any:
        client = TestClient(app=create_app())
        opened.append(client.__enter__())
        return opened[-1]

    yield open_client
    for client in opened:
        client.__exit__(None, None, None)


@pytest.fixture
def client(new_client: Callable[[], Any]) -> Any:
    return new_client()


def sign_up(client: Any, display_name: str, email: str | None = None) -> dict[str, Any]:
    response = client.post(
        "/api/accounts",
        json={
            "display_name": display_name,
            "email": email or unique_email(display_name),
            "password": PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    user: dict[str, Any] = response.json()
    return user


def create_association(client: Any, name: str = "Jardin partagé des Lilas") -> dict[str, Any]:
    response = client.post("/api/associations", json={"name": name})
    assert response.status_code == 201, response.text
    association: dict[str, Any] = response.json()
    return association


def add_member(
    client: Any, association_id: str, display_name: str, email: str, role: str = "volunteer"
) -> Any:
    return client.post(
        f"/api/associations/{association_id}/members",
        json={"display_name": display_name, "email": email, "role": role},
    )
