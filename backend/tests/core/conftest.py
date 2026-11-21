import asyncio
import html
import os
import re
import time
import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Any, NamedTuple

import httpx
import pytest
from litestar.testing import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.page import Element, heading_of, lines_of, parse, part

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
def new_client(server: Any) -> Callable[[], Any]:
    """Opens extra clients, each with its own cookies (its own browser)."""

    def open_client() -> Any:
        client = TestClient(app=server.app)
        # Requests run on the worker's event loop, where the database connections live.
        client.blocking_portal = server.blocking_portal
        return client

    return open_client


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


def patched(response: Any) -> str:
    """The events of an action's response, each `datastar-patch-elements` one with the HTML it
    patches in, rebuilt from its `data: elements` lines as the browser does, after its other
    lines."""
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")
    events = []
    for event in response.text.split("\n\n"):
        lines = event.split("\n")
        if "event: datastar-patch-elements" not in lines:
            events.append(event)
            continue
        prefix = "data: elements "
        elements = [line.removeprefix(prefix) for line in lines if line.startswith(prefix)]
        others = [line for line in lines if not line.startswith(prefix)]
        events.append("\n".join([*others, "\n".join(elements)]))
    return "\n\n".join(events)


def shown(response: Any) -> str:
    """The events of an action's response, as `patched` gives them, unescaped: what the browser
    is sent to show."""
    return html.unescape(patched(response))


def heading(response: Any) -> str:
    """The text of the first heading the page shows."""
    return heading_of(response.text)


def break_the_mailer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Points the mailer at a port where nothing listens, so sending fails."""
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "1")


def sign_in(client: Any, email: str, password: str = PASSWORD, **kwargs: Any) -> Any:
    """Submits Sign in, as the screen does."""
    return client.post("/sign-in", json={"email": email, "password": password}, **kwargs)


def sign_up(client: Any, display_name: str, email: str | None = None) -> dict[str, Any]:
    """Signs up, confirms the email via Mailpit, and signs in."""
    email = email or unique_email(display_name)
    response = create_account(client, display_name, email)
    assert response.status_code == 200, response.text
    assert email in response.text, response.text

    assert confirm_email(client, latest_verification_token(email)).status_code == 200
    assert "window.location" in shown(sign_in(client, email))
    return {"id": user_id_of(email), "display_name": display_name, "email": email}


def run_sql(sql: str, token: str = "", **params: Any) -> Any:
    """Runs `sql` with `token` and `params` as its parameters, and returns its first value, if
    any."""
    rows = run_sql_rows(sql, token=token, **params)
    return rows[0][0] if rows and rows[0] else None


_database: dict[str, Any] = {}


def run_sql_rows(sql: str, **params: Any) -> list[tuple[Any, ...]]:
    """Runs `sql` with `params` as its parameters, and returns its rows, if any. The tests of a
    process share one event loop and one connection for it."""
    if not _database:
        _database["loop"] = asyncio.new_event_loop()
        _database["engine"] = create_async_engine(os.environ["DATABASE_URL"], pool_size=1)

    async def run() -> list[tuple[Any, ...]]:
        async with _database["engine"].begin() as connection:
            result = await connection.execute(text(sql), params)
            return [tuple(row) for row in result] if result.returns_rows else []

    rows: list[tuple[Any, ...]] = _database["loop"].run_until_complete(run())
    return rows


def user_id_of(email: str) -> str:
    """The id of the user who has `email`, read from the database: no screen shows it."""
    user_id = run_sql("SELECT id FROM user_account WHERE lower(email) = lower(:email)", email=email)
    assert user_id, f"no user has {email}"
    return str(user_id)


def signed_in_as(client: Any) -> str | None:
    """The display name the header of `/` shows the user signed in on `client`, or None when `/`
    shows Sign in."""
    response = client.get("/")
    assert response.status_code == 200
    buttons = [b for b in parse(response.text).elements("button") if "user-button" in b.classes]
    if not buttons:
        assert heading(response) == "Sign in", response.text
        return None
    assert len(buttons) == 1, buttons
    return buttons[0].text.removesuffix(" ▾")


def unique_slug() -> str:
    """Slugs are unique across associations, so each test uses fresh ones."""
    return f"a-{uuid.uuid4().hex[:12]}"


def create_association(
    client: Any, name: str = "Jardin partagé des Lilas", slug: str | None = None
) -> dict[str, Any]:
    """Creates an association on New association; its id is read from the database."""
    slug = slug or unique_slug()
    text = shown(client.post("/association/new", json={"name": name, "slug": slug}))
    assert f"/association/{slug}" in text, text
    association_id = run_sql("SELECT id FROM association WHERE slug = :slug", slug=slug)
    return {"id": str(association_id), "name": name, "slug": slug}


def add_member(
    client: Any, slug: str, display_name: str, email: str, role: str = "volunteer"
) -> dict[str, Any]:
    """Adds a member with "Add a member" on Members; their user id is read from the database."""
    text = shown(
        client.post(
            f"/association/{slug}/members",
            json={"displayName": display_name, "email": email, "role": role},
        )
    )
    assert " added." in text, text
    return {"user_id": user_id_of(email), "email": email}


def member_line(client: Any, slug: str, email: str) -> str:
    """What the line of the member with `email` shows on Members, its spaces collapsed, e.g.
    "Chloé not joined yet chloe@example.org Volunteer"; Members shows the first five lines only,
    until "Show all"."""
    response = client.get(f"/association/{slug}/members")
    assert response.status_code == 200
    texts = lines_of(part(response.text, "main"))
    found = [text for text in texts if f" {email} " in f" {text} "]
    assert len(found) == 1, f"{email} in {texts}"
    return found[0]


def members_roles(client: Any, slug: str) -> dict[str, str]:
    """The role of each member that Members shows, by display name, e.g. {"Alice": "manager"}:
    the first five only, until "Show all"."""
    response = client.get(f"/association/{slug}/members")
    assert response.status_code == 200
    roles = {}
    for item in parse(response.text).first("main").outermost("li"):
        found = [e for e in item.elements("span") if "role" in e.classes]
        assert len(found) == 1, item
        [role] = [name for name in found[0].classes if name != "role"]
        name = item.first("div").text_with(lambda e: "" if e.tag in ("span", "div") else None)
        roles[name] = role
    return roles


def change_role(client: Any, slug: str, user_id: str, role: str) -> Any:
    """Saves the edit dialog of a member on Members, with `role`."""
    return client.post(f"/association/{slug}/members/{user_id}/role", json={"role": role})


def remove_member(client: Any, slug: str, user_id: str) -> Any:
    """Confirms "Remove from the association" for a member on Members."""
    return client.post(f"/association/{slug}/members/{user_id}/remove", json={})


def send_member_link(client: Any, slug: str, user_id: str, **kwargs: Any) -> Any:
    """Confirms "Send link" in the edit dialog of a member on Members."""
    return client.post(f"/association/{slug}/members/{user_id}/send-link", json={}, **kwargs)


def revoke_member_link(client: Any, slug: str, user_id: str) -> Any:
    """Confirms "Revoke link" in the edit dialog of a member on Members."""
    return client.post(f"/association/{slug}/members/{user_id}/revoke-link", json={})


def rename_association(client: Any, slug: str, name: str) -> Any:
    """Saves "Rename the association" on Members, with `name`."""
    return client.post(f"/association/{slug}/rename", json={"name": name})


def change_identifier(client: Any, slug: str, new_slug: str) -> Any:
    """Saves "Change the association identifier" on Members, with `new_slug`."""
    return client.post(f"/association/{slug}/identifier", json={"slug": new_slug})


def delete_association(client: Any, slug: str) -> Any:
    """Confirms "Delete the association" on Members."""
    return client.post(f"/association/{slug}/delete", json={})


class Listed(NamedTuple):
    """An association as My associations lists it."""

    name: str
    """The text of its first link, its name."""
    text: str
    """What it shows outside its registrations, its spaces collapsed."""
    lines: list[str]
    """What each of its registrations shows, in order, its spaces collapsed."""


def listed(fragment: str) -> list[Listed]:
    """The associations that a piece of HTML lists, each an outermost `<li>` whose nested `<li>`
    are its registrations."""
    associations = []
    for item in parse(fragment).outermost("li"):
        registrations = item.outermost("li")
        links = [link for link in item.elements("a") if not _within(link, registrations)]
        name = links[0].text if links else ""
        text = item.text_with(lambda e: "" if e.tag == "li" else None)
        associations.append(Listed(name, text, [line.text for line in registrations]))
    return associations


def _within(element: Element, ancestors: list[Element]) -> bool:
    parent = element.parent
    while parent is not None:
        if any(parent is ancestor for ancestor in ancestors):
            return True
        parent = parent.parent
    return False


def my_associations_listed(client: Any) -> list[Listed]:
    """The associations that My associations lists to the signed-in user."""
    response = client.get("/")
    assert response.status_code == 200
    return listed(part(response.text, "main"))


def names_listed(client: Any) -> list[str]:
    """The names of the associations that My associations lists, in order."""
    return [association.name for association in my_associations_listed(client)]
