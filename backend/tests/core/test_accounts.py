import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    PASSWORD,
    add_member,
    create_account,
    create_association,
    sign_up,
    unique_email,
)

# POST /api/session


def test_post_api_session_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    user = sign_up(client, "Alice", email)
    browser = new_client()

    response = browser.post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json() == {**user, "superuser": False}
    assert "session" in response.headers.get("set-cookie", "")
    assert browser.get("/api/session").json() == {**user, "superuser": False}


def test_post_api_session_ignores_the_case_of_the_email(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = new_client().post(
        "/api/session", json={"email": email.upper(), "password": PASSWORD}
    )

    assert response.status_code == 200


def test_post_api_session_401_does_not_say_which_credential_is_wrong(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    association = create_association(client)
    volunteer_email = unique_email("Chloe")
    add_member(client, association["id"], "Chloé", volunteer_email)
    unconfirmed_email = unique_email("Bruno")
    browser = new_client()
    create_account(browser, "Bruno", unconfirmed_email)

    wrong_password = browser.post("/api/session", json={"email": email, "password": "nope-nope"})
    unknown_email = browser.post(
        "/api/session", json={"email": unique_email("Nobody"), "password": PASSWORD}
    )
    no_account = browser.post("/api/session", json={"email": volunteer_email, "password": PASSWORD})
    unconfirmed = browser.post(
        "/api/session", json={"email": unconfirmed_email, "password": PASSWORD}
    )

    responses = (wrong_password, unknown_email, no_account, unconfirmed)
    assert [r.status_code for r in responses] == [401] * 4
    assert len({r.text for r in responses}) == 1
    assert "error" in wrong_password.json()
    assert browser.get("/api/session").status_code == 401


def test_r16_sign_in_replaces_a_session_id_planted_in_the_browser(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    planted = uuid.uuid4().hex
    victim = new_client()
    victim.cookies.set("session", planted)
    attacker = new_client()
    attacker.cookies.set("session", planted)

    response = victim.post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.cookies.get("session") not in (None, planted)
    assert attacker.get("/api/session").status_code == 401


def test_r16_sign_in_replaces_the_id_of_an_existing_session(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    attacker = new_client()
    sign_up(attacker, "Mallory")
    planted = attacker.cookies.get("session")
    victim = new_client()
    victim.cookies.set("session", planted)

    response = victim.post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.cookies.get("session") not in (None, planted)
    assert attacker.get("/api/session").status_code == 401


def test_post_api_session_superuser_is_true_for_superuser_email_ignoring_case(
    new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    email = unique_email("Alice")
    monkeypatch.setenv("SUPERUSER_EMAIL", email.upper())
    client = new_client()
    sign_up(client, "Alice", email)

    response = new_client().post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.status_code == 200
    assert response.json()["superuser"] is True


def test_post_api_session_superuser_is_false_for_another_email(
    new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SUPERUSER_EMAIL", unique_email("Root"))
    client = new_client()
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = new_client().post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.json()["superuser"] is False


def test_post_api_session_superuser_is_false_when_superuser_email_is_unset(
    new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SUPERUSER_EMAIL", raising=False)
    client = new_client()
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = new_client().post("/api/session", json={"email": email, "password": PASSWORD})

    assert response.json()["superuser"] is False


# GET /api/session


def test_get_api_session_tells_the_superuser(
    new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    email = unique_email("Alice")
    monkeypatch.setenv("SUPERUSER_EMAIL", email)
    client = new_client()
    sign_up(client, "Alice", email)

    response = client.get("/api/session")

    assert response.status_code == 200
    assert response.json()["superuser"] is True


def test_get_api_session_401_when_signed_out(client: Any) -> None:
    response = client.get("/api/session")

    assert response.status_code == 401
    assert "error" in response.json()


# DELETE /api/session


def test_delete_api_session_signs_out(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.delete("/api/session")

    assert response.status_code == 204
    assert client.get("/api/session").status_code == 401
    assert 'type="password"' in client.get("/").text
