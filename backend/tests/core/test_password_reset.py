import asyncio
import os
import re
import time
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from tests.core.conftest import (
    PASSWORD,
    add_member,
    create_association,
    email_count,
    latest_email,
    latest_reset_token,
    sign_up,
    unique_email,
)

NEW_PASSWORD = "battery staple"

ENGLISH = {
    "Subject": "Reset your password",
    "Text": "Choose a new password by opening this link, valid for one hour:",
}
FRENCH = {
    "Subject": "Réinitialisez votre mot de passe",
    "Text": "Choisissez un nouveau mot de passe en ouvrant ce lien, valable une heure :",
}


def ask_for_reset(client: Any, email: str, accept_language: str | None = None) -> Any:
    headers = {} if accept_language is None else {"Accept-Language": accept_language}
    return client.post("/api/accounts/password-reset", json={"email": email}, headers=headers)


def reset(client: Any, token: str, password: str = NEW_PASSWORD) -> Any:
    return client.post(
        "/api/accounts/password-reset/confirm", json={"token": token, "password": password}
    )


def can_sign_in(new_client: Callable[[], Any], email: str, password: str) -> bool:
    response = new_client().post("/api/session", json={"email": email, "password": password})
    return bool(response.status_code == 200)


def run_sql(sql: str, token: str) -> Any:
    """Runs `sql` on the reset token `token`, and returns its first value, if any."""

    async def run() -> Any:
        engine = create_async_engine(os.environ["DATABASE_URL"])
        async with engine.begin() as connection:
            result = await connection.execute(text(sql), {"token": token})
            value = result.scalar() if result.returns_rows else None
        await engine.dispose()
        return value

    return asyncio.run(run())


def expires_in(token: str) -> timedelta:
    return run_sql(  # type: ignore[no-any-return]
        "SELECT expires_at - now() FROM password_reset_token WHERE token = :token", token
    )


def expire(token: str) -> None:
    """Moves the reset token's expiry into the past, as if its hour had elapsed."""
    run_sql(
        "UPDATE password_reset_token SET expires_at = now() - interval '1 second'"
        " WHERE token = :token",
        token,
    )


def assert_no_email_sent(email: str) -> None:
    time.sleep(0.5)
    assert email_count(email) == 0


# POST /api/accounts/password-reset


def test_r21_sends_a_reset_link_to_a_user_with_a_password(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = ask_for_reset(new_client(), email)

    assert response.status_code == 204
    sent = latest_email(email)
    assert sent["Subject"] == ENGLISH["Subject"]
    assert sent["Text"].startswith(ENGLISH["Text"])
    assert re.search(r"/reset-password\?token=[\w-]+", sent["Text"])


@pytest.mark.parametrize("accept_language", ["fr", "fr-FR,fr;q=0.9,en;q=0.8"])
def test_r21_reset_email_is_in_french_when_the_request_prefers_french(
    client: Any, new_client: Callable[[], Any], accept_language: str
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    ask_for_reset(new_client(), email, accept_language)

    sent = latest_email(email)
    assert sent["Subject"] == FRENCH["Subject"]
    assert sent["Text"].startswith(FRENCH["Text"])
    assert re.search(r"/reset-password\?token=[\w-]+", sent["Text"])


def test_r21_reset_email_is_in_english_otherwise(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    ask_for_reset(new_client(), email, "de")

    assert latest_email(email)["Subject"] == ENGLISH["Subject"]


def test_r21_ignores_the_case_of_the_email(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    ask_for_reset(new_client(), email.upper())

    latest_reset_token(email)  # raises if no reset email was sent


def test_r21_sends_a_reset_link_to_a_user_whose_email_is_not_confirmed(client: Any) -> None:
    email = unique_email("Bruno")
    client.post(
        "/api/accounts", json={"display_name": "Bruno", "email": email, "password": PASSWORD}
    )

    response = ask_for_reset(client, email)

    assert response.status_code == 204
    latest_reset_token(email)


def test_password_reset_sends_nothing_to_a_user_without_a_password(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    chloe_email = unique_email("Chloe")
    add_member(client, association["id"], "Chloé", chloe_email)

    response = ask_for_reset(new_client(), chloe_email)

    assert response.status_code == 204
    assert_no_email_sent(chloe_email)


def test_password_reset_sends_nothing_to_an_unknown_email(client: Any) -> None:
    email = unique_email("Nobody")

    response = ask_for_reset(client, email)

    assert response.status_code == 204
    assert_no_email_sent(email)


def test_password_reset_204_when_the_email_cannot_be_sent(
    client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    monkeypatch.setenv("SMTP_HOST", "localhost")
    monkeypatch.setenv("SMTP_PORT", "1")

    response = ask_for_reset(new_client(), email)

    assert response.status_code == 204


def test_r8_a_new_reset_request_invalidates_the_previous_link(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)
    first_token = latest_reset_token(email)
    time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

    ask_for_reset(browser, email)

    second_token = latest_reset_token(email)
    assert second_token != first_token
    assert reset(browser, first_token).status_code == 404
    assert reset(browser, second_token).status_code == 200


@pytest.mark.parametrize("body", [{}, {"email": ""}, {"email": "not-an-email"}])
def test_password_reset_400_when_the_email_is_missing_empty_or_invalid(
    client: Any, body: dict[str, str]
) -> None:
    response = client.post("/api/accounts/password-reset", json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# POST /api/accounts/password-reset/confirm


def test_r22_replaces_the_password(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)

    response = reset(browser, latest_reset_token(email))

    assert response.status_code == 200
    assert can_sign_in(new_client, email, NEW_PASSWORD)
    assert not can_sign_in(new_client, email, PASSWORD)


def test_r22_signs_the_user_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    user = sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)

    response = reset(browser, latest_reset_token(email))

    assert response.json() == {**user, "superuser": False}
    assert "session" in response.headers.get("set-cookie", "")
    assert browser.get("/api/session").json() == {**user, "superuser": False}


def test_r22_tells_the_superuser(
    new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    email = unique_email("Root")
    monkeypatch.setenv("SUPERUSER_EMAIL", email)
    sign_up(new_client(), "Root", email)
    browser = new_client()
    ask_for_reset(browser, email)

    response = reset(browser, latest_reset_token(email))

    assert response.json()["superuser"] is True


def test_r22_keeps_the_other_sessions_signed_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    user = sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)

    reset(browser, latest_reset_token(email))

    assert client.get("/api/session").json() == {**user, "superuser": False}


def test_r22_confirms_an_unconfirmed_email(client: Any, new_client: Callable[[], Any]) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    bruno_email = unique_email("Bruno")
    member = add_member(client, association["id"], "Bruno", bruno_email).json()
    bruno = new_client()
    bruno.post(
        "/api/accounts", json={"display_name": "Bruno", "email": bruno_email, "password": PASSWORD}
    )
    ask_for_reset(bruno, bruno_email)

    response = reset(bruno, latest_reset_token(bruno_email))

    assert response.status_code == 200
    assert can_sign_in(new_client, bruno_email, NEW_PASSWORD)
    members = client.get(f"/api/associations/{association['id']}").json()["members"]
    bruno_member = next(m for m in members if m["user_id"] == member["user_id"])
    assert bruno_member["email_verified"] is True


def test_r22_the_link_works_only_once(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)
    token = latest_reset_token(email)
    reset(browser, token)

    response = reset(new_client(), token, "another password")

    assert response.status_code == 404
    assert "error" in response.json()
    assert can_sign_in(new_client, email, NEW_PASSWORD)


def test_r16_reset_replaces_a_session_id_planted_in_the_browser(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    planted = uuid.uuid4().hex
    victim = new_client()
    victim.cookies.set("session", planted)
    attacker = new_client()
    attacker.cookies.set("session", planted)
    ask_for_reset(victim, email)

    response = reset(victim, latest_reset_token(email))

    assert response.status_code == 200
    assert response.cookies.get("session") not in (None, planted)
    assert attacker.get("/api/session").status_code == 401


def test_password_reset_confirm_404_when_the_token_is_unknown(client: Any) -> None:
    response = reset(client, "unknown-token")

    assert response.status_code == 404
    assert "error" in response.json()
    assert client.get("/api/session").status_code == 401


def test_password_reset_token_expires_after_one_hour(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)
    token = latest_reset_token(email)
    assert timedelta(minutes=59) < expires_in(token) <= timedelta(hours=1)
    expire(token)

    response = reset(browser, token)

    assert response.status_code == 404
    assert can_sign_in(new_client, email, PASSWORD)


def test_password_reset_confirm_400_when_the_password_is_too_short_and_the_link_still_works(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_reset(browser, email)
    token = latest_reset_token(email)

    response = reset(browser, token, "1234567")

    assert response.status_code == 400
    assert "error" in response.json()
    assert browser.get("/api/session").status_code == 401
    assert can_sign_in(new_client, email, PASSWORD)
    assert reset(browser, token, "12345678").status_code == 200


@pytest.mark.parametrize("body", [{"token": "t"}, {"password": NEW_PASSWORD}])
def test_password_reset_confirm_400_when_a_field_is_missing(
    client: Any, body: dict[str, str]
) -> None:
    response = client.post("/api/accounts/password-reset/confirm", json=body)

    assert response.status_code == 400
    assert "error" in response.json()
