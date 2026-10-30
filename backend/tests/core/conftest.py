import os
import re
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime
from typing import Any

import httpx
import pytest
from litestar.testing import TestClient

from gilda.app import create_app

PASSWORD = "correct horse"
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://localhost:18025")


def unique_email(name: str) -> str:
    """Each test uses fresh emails, so tests never see each other's users."""
    return f"{name.lower()}-{uuid.uuid4().hex[:12]}@example.org"


def latest_verification_token(email: str, timeout: float = 5.0) -> str:
    """Reads the confirmation link Mailpit caught for `email`, and returns its token."""
    deadline = time.monotonic() + timeout
    while True:
        response = httpx.get(f"{MAILPIT_URL}/api/v1/search", params={"query": f"to:{email}"})
        messages = response.json()["messages"]
        if messages:
            # Mailpit IDs are not ordered by time; Created has millisecond precision.
            latest = max(messages, key=lambda m: datetime.fromisoformat(m["Created"]))
            text = httpx.get(f"{MAILPIT_URL}/api/v1/message/{latest['ID']}").json()["Text"]
            match = re.search(r"token=([\w-]+)", text)
            assert match, f"no verification link in the email sent to {email}"
            return match.group(1)
        if time.monotonic() > deadline:
            raise AssertionError(f"no email was sent to {email}")
        time.sleep(0.2)


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
    """Signs up, confirms the email via Mailpit, and signs in."""
    email = email or unique_email(display_name)
    response = client.post(
        "/api/accounts",
        json={"display_name": display_name, "email": email, "password": PASSWORD},
    )
    assert response.status_code == 201, response.text
    user: dict[str, Any] = response.json()

    token = latest_verification_token(email)
    assert client.post("/api/accounts/verify", json={"token": token}).status_code == 200
    sign_in = client.post("/api/session", json={"email": email, "password": PASSWORD})
    assert sign_in.status_code == 200
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
