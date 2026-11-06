import asyncio
import html
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
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from gilda.app import create_app

PASSWORD = "correct horse"
MAILPIT_URL = os.environ.get("MAILPIT_URL", "http://localhost:18025")


def unique_email(name: str) -> str:
    """Each test uses fresh emails, so tests never see each other's users."""
    return f"{name.lower()}-{uuid.uuid4().hex[:12]}@example.org"


def latest_email(email: str, timeout: float = 5.0) -> dict[str, str]:
    """The latest email Mailpit caught for `email`, as its Subject and Text."""
    deadline = time.monotonic() + timeout
    while True:
        response = httpx.get(f"{MAILPIT_URL}/api/v1/search", params={"query": f"to:{email}"})
        messages = response.json()["messages"]
        if messages:
            # Mailpit IDs are not ordered by time; Created has millisecond precision.
            latest = max(messages, key=lambda m: datetime.fromisoformat(m["Created"]))
            message = httpx.get(f"{MAILPIT_URL}/api/v1/message/{latest['ID']}").json()
            return {"Subject": message["Subject"], "Text": message["Text"]}
        if time.monotonic() > deadline:
            raise AssertionError(f"no email was sent to {email}")
        time.sleep(0.2)


def latest_verification_token(email: str, timeout: float = 5.0) -> str:
    """Reads the confirmation link Mailpit caught for `email`, and returns its token."""
    text = latest_email(email, timeout)["Text"]
    match = re.search(r"token=([\w-]+)", text)
    assert match, f"no verification link in the email sent to {email}"
    return match.group(1)


def latest_reset_token(email: str, timeout: float = 5.0) -> str:
    """Reads the reset link Mailpit caught for `email`, and returns its token."""
    text = latest_email(email, timeout)["Text"]
    match = re.search(r"/reset-password\?token=([\w-]+)", text)
    assert match, f"no reset link in the email sent to {email}"
    return match.group(1)


def latest_access_token(email: str, timeout: float = 5.0) -> str:
    """Reads the access link Mailpit caught for `email`, and returns its token."""
    text = latest_email(email, timeout)["Text"]
    match = re.search(r"/access\?token=([\w-]+)", text)
    assert match, f"no access link in the email sent to {email}"
    return match.group(1)


def email_count(email: str) -> int:
    """How many emails Mailpit caught for `email`."""
    response = httpx.get(f"{MAILPIT_URL}/api/v1/search", params={"query": f"to:{email}"})
    return len(response.json()["messages"])


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
        # Advanced Alchemy disposes only the first app's engine of a process: the
        # following ones get renamed state keys that its shutdown does not look up.
        for value in client.app.state.dict().values():
            if isinstance(value, AsyncEngine):
                client.blocking_portal.call(value.dispose)
        client.__exit__(None, None, None)


@pytest.fixture
def client(new_client: Callable[[], Any]) -> Any:
    return new_client()


def create_account(
    client: Any, display_name: str, email: str, password: str = PASSWORD, **kwargs: Any
) -> Any:
    """Submits Create an account, as the screen does."""
    return client.post(
        "/signup",
        json={"displayName": display_name, "email": email, "password": password},
        **kwargs,
    )


def confirm_email(client: Any, token: str) -> Any:
    """Runs the action of Confirm email, as the page does."""
    return client.post("/verify-email", json={"token": token})


def ask_for_reset(client: Any, email: str, **kwargs: Any) -> Any:
    """Submits Forgot password, as the screen does."""
    return client.post("/forgot-password", json={"email": email}, **kwargs)


def reset_password(client: Any, token: str, password: str) -> Any:
    """Submits Reset password, as the screen does."""
    return client.post("/reset-password", json={"token": token, "password": password})


def ask_for_link(client: Any, email: str, **kwargs: Any) -> Any:
    """Submits Sign-in link, as the screen does."""
    return client.post("/sign-in-link", json={"email": email}, **kwargs)


def open_link(client: Any, token: str) -> Any:
    """Runs the action of Access link, as the page does."""
    return client.post("/access", json={"token": token})


def shown(response: Any) -> str:
    """The text of an action's response, as the browser shows it."""
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    return html.unescape(response.text)


def heading(response: Any) -> str:
    match = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", response.text, re.DOTALL)
    assert match, f"no heading in {response.text}"
    return match.group(1)


def break_the_mailer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Points the mailer at a port where nothing listens, so sending fails."""
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "1")


def sign_up(client: Any, display_name: str, email: str | None = None) -> dict[str, Any]:
    """Signs up, confirms the email via Mailpit, and signs in."""
    email = email or unique_email(display_name)
    response = create_account(client, display_name, email)
    assert response.status_code == 200, response.text
    assert email in response.text, response.text

    assert confirm_email(client, latest_verification_token(email)).status_code == 200
    sign_in = client.post("/api/session", json={"email": email, "password": PASSWORD})
    assert sign_in.status_code == 200
    user: dict[str, Any] = sign_in.json()
    del user["superuser"]
    return user


def run_sql(sql: str, token: str) -> Any:
    """Runs `sql` with this `token` as its parameter, and returns its first value, if any."""

    async def run() -> Any:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as connection:
            result = await connection.execute(text(sql), {"token": token})
            value = result.scalar() if result.returns_rows else None
        await engine.dispose()
        return value

    return asyncio.run(run())


def unique_slug() -> str:
    """Slugs are unique across associations, so each test uses fresh ones."""
    return f"a-{uuid.uuid4().hex[:12]}"


def create_association(
    client: Any, name: str = "Jardin partagé des Lilas", slug: str | None = None
) -> dict[str, Any]:
    response = client.post("/api/associations", json={"name": name, "slug": slug or unique_slug()})
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
