import re
import time
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    PASSWORD,
    add_member,
    create_association,
    email_count,
    latest_email,
    sign_up,
    unique_email,
)

ENGLISH = {
    "Subject": "Your sign-in link",
    "Text": "Sign in by opening this link. Keep this email: the link stays valid\n"
    "until you revoke it.",
}
FRENCH = {
    "Subject": "Votre lien de connexion",
    "Text": "Connectez-vous en ouvrant ce lien. Conservez cet e-mail : le lien\n"
    "reste valable jusqu'à ce que vous le révoquiez.",
}


def ask_for_link(client: Any, email: str, accept_language: str | None = None) -> Any:
    headers = {} if accept_language is None else {"Accept-Language": accept_language}
    return client.post("/api/access-link", json={"email": email}, headers=headers)


def latest_access_token(email: str) -> str:
    """Reads the access link Mailpit caught for `email`, and returns its token."""
    text = latest_email(email)["Text"]
    match = re.search(r"/access\?token=([\w-]+)", text)
    assert match, f"no access link in the email sent to {email}"
    return match.group(1)


def open_link(client: Any, token: str) -> Any:
    return client.post("/api/session/access-link", json={"token": token})


def normalized(text: str) -> str:
    """Email bodies may be rewrapped; compare them with single spaces."""
    return " ".join(text.split())


def manager_with_member(
    client: Any, email: str | None = None
) -> tuple[dict[str, Any], dict[str, Any], str]:
    """Alice manages an association, where she adds Chloé, a user without a password."""
    sign_up(client, "Alice")
    association = create_association(client)
    chloe_email = email or unique_email("Chloe")
    chloe = add_member(client, association["id"], "Chloé", chloe_email).json()
    return association, chloe, chloe_email


def member(client: Any, association_id: str, user_id: str) -> dict[str, Any]:
    members = client.get(f"/api/associations/{association_id}").json()["members"]
    return next(m for m in members if m["user_id"] == user_id)  # type: ignore[no-any-return]


def assert_no_email_sent(email: str) -> None:
    time.sleep(0.5)
    assert email_count(email) == 0


# POST /api/access-link


def test_r24_sends_the_access_link_to_a_user_with_a_password(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    response = ask_for_link(new_client(), email)

    assert response.status_code == 204
    sent = latest_email(email)
    assert sent["Subject"] == ENGLISH["Subject"]
    assert normalized(sent["Text"]).startswith(normalized(ENGLISH["Text"]))
    assert re.search(r"/access\?token=[\w-]+", sent["Text"])


def test_r24_sends_the_access_link_to_a_member_without_a_password(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)

    response = ask_for_link(new_client(), chloe_email)

    assert response.status_code == 204
    latest_access_token(chloe_email)  # raises if no access link was sent


@pytest.mark.parametrize("accept_language", ["fr", "fr-FR,fr;q=0.9,en;q=0.8"])
def test_r24_access_link_email_is_in_french_when_the_request_prefers_french(
    client: Any, new_client: Callable[[], Any], accept_language: str
) -> None:
    _, _, chloe_email = manager_with_member(client)

    ask_for_link(new_client(), chloe_email, accept_language)

    sent = latest_email(chloe_email)
    assert sent["Subject"] == FRENCH["Subject"]
    assert normalized(sent["Text"]).startswith(normalized(FRENCH["Text"]))
    assert re.search(r"/access\?token=[\w-]+", sent["Text"])


def test_r24_access_link_email_is_in_english_otherwise(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)

    ask_for_link(new_client(), chloe_email, "de")

    assert latest_email(chloe_email)["Subject"] == ENGLISH["Subject"]


def test_r24_ignores_the_case_of_the_email(client: Any, new_client: Callable[[], Any]) -> None:
    _, _, chloe_email = manager_with_member(client)

    ask_for_link(new_client(), chloe_email.upper())

    latest_access_token(chloe_email)


def test_r25_a_new_request_sends_the_same_link(client: Any, new_client: Callable[[], Any]) -> None:
    _, _, chloe_email = manager_with_member(client)
    browser = new_client()
    ask_for_link(browser, chloe_email)
    first_token = latest_access_token(chloe_email)
    time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

    ask_for_link(browser, chloe_email)

    assert email_count(chloe_email) == 2
    assert latest_access_token(chloe_email) == first_token
    assert open_link(new_client(), first_token).status_code == 200


def test_access_link_sends_nothing_to_an_unknown_email(client: Any) -> None:
    email = unique_email("Nobody")

    response = ask_for_link(client, email)

    assert response.status_code == 204
    assert_no_email_sent(email)


@pytest.mark.parametrize("body", [{}, {"email": ""}, {"email": "not-an-email"}])
def test_access_link_400_when_the_email_is_missing_empty_or_invalid(
    client: Any, body: dict[str, str]
) -> None:
    response = client.post("/api/access-link", json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# POST /api/session/access-link


def test_access_link_signs_a_member_without_a_password_in(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, chloe, chloe_email = manager_with_member(client)
    browser = new_client()
    ask_for_link(browser, chloe_email)

    response = open_link(browser, latest_access_token(chloe_email))

    expected = {
        "id": chloe["user_id"],
        "display_name": "Chloé",
        "email": chloe_email,
        "superuser": False,
    }
    assert response.status_code == 200
    assert response.json() == expected
    assert "session" in response.headers.get("set-cookie", "")
    assert browser.get("/api/session").json() == expected


def test_access_link_signs_a_user_with_a_password_in(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    user = sign_up(client, "Alice", email)
    browser = new_client()
    ask_for_link(browser, email)

    response = open_link(browser, latest_access_token(email))

    assert response.json() == {**user, "superuser": False}
    assert browser.get("/api/session").json() == {**user, "superuser": False}


def test_access_link_confirms_the_email(client: Any, new_client: Callable[[], Any]) -> None:
    association, chloe, chloe_email = manager_with_member(client)
    browser = new_client()
    ask_for_link(browser, chloe_email)

    open_link(browser, latest_access_token(chloe_email))

    assert member(client, association["id"], chloe["user_id"])["email_verified"] is True


def test_access_link_lets_a_user_with_an_unconfirmed_email_sign_in_with_their_password(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Bruno")
    client.post(
        "/api/accounts", json={"display_name": "Bruno", "email": email, "password": PASSWORD}
    )
    ask_for_link(client, email)

    open_link(client, latest_access_token(email))

    response = new_client().post("/api/session", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200


def test_access_link_stays_usable(client: Any, new_client: Callable[[], Any]) -> None:
    _, chloe, chloe_email = manager_with_member(client)
    ask_for_link(new_client(), chloe_email)
    token = latest_access_token(chloe_email)
    first = new_client()
    open_link(first, token)
    first.delete("/api/session")

    second = new_client()
    response = open_link(second, token)

    assert response.status_code == 200
    assert second.get("/api/session").json()["id"] == chloe["user_id"]


def test_r16_access_link_replaces_a_session_id_planted_in_the_browser(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)
    planted = uuid.uuid4().hex
    victim = new_client()
    victim.cookies.set("session", planted)
    attacker = new_client()
    attacker.cookies.set("session", planted)
    ask_for_link(victim, chloe_email)

    response = open_link(victim, latest_access_token(chloe_email))

    assert response.status_code == 200
    assert response.cookies.get("session") not in (None, planted)
    assert attacker.get("/api/session").status_code == 401


def test_session_access_link_404_when_the_token_is_unknown(client: Any) -> None:
    response = open_link(client, "unknown-token")

    assert response.status_code == 404
    assert "error" in response.json()
    assert client.get("/api/session").status_code == 401


@pytest.mark.parametrize("body", [{}, {"token": ""}])
def test_session_access_link_400_when_the_token_is_missing_or_empty(
    client: Any, body: dict[str, str]
) -> None:
    response = client.post("/api/session/access-link", json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# DELETE /api/access-link


def test_r23_revoking_the_link_makes_it_unusable(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)
    chloe = new_client()
    ask_for_link(chloe, chloe_email)
    token = latest_access_token(chloe_email)
    open_link(chloe, token)

    response = chloe.delete("/api/access-link")

    assert response.status_code == 204
    assert open_link(new_client(), token).status_code == 404


def test_r23_revoking_the_link_signs_out_the_sessions_it_opened(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)
    ask_for_link(new_client(), chloe_email)
    token = latest_access_token(chloe_email)
    phone = new_client()
    open_link(phone, token)
    laptop = new_client()
    open_link(laptop, token)

    laptop.delete("/api/access-link")

    assert phone.get("/api/session").status_code == 401
    assert laptop.get("/api/session").status_code == 401


def test_r23_revoking_the_link_keeps_password_sessions_signed_in(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    user = sign_up(client, "Alice", email)
    ask_for_link(new_client(), email)
    token = latest_access_token(email)
    phone = new_client()
    open_link(phone, token)

    response = client.delete("/api/access-link")

    assert response.status_code == 204
    assert client.get("/api/session").json() == {**user, "superuser": False}
    assert phone.get("/api/session").status_code == 401


def test_r25_after_revoking_a_new_request_sends_a_new_link(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    ask_for_link(client, email)
    old_token = latest_access_token(email)
    client.delete("/api/access-link")
    time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

    ask_for_link(client, email)

    new_token = latest_access_token(email)
    assert new_token != old_token
    assert open_link(new_client(), new_token).status_code == 200


def test_delete_api_access_link_204_without_a_link(client: Any) -> None:
    sign_up(client, "Alice")

    assert client.delete("/api/access-link").status_code == 204


def test_delete_api_access_link_401_when_signed_out(client: Any) -> None:
    response = client.delete("/api/access-link")

    assert response.status_code == 401
    assert "error" in response.json()


# DELETE /api/associations/{id}/members/{user_id}/access-link


def test_access_link_shows_whether_a_member_has_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, chloe, chloe_email = manager_with_member(client)
    assert member(client, association["id"], chloe["user_id"])["access_link"] is False

    ask_for_link(new_client(), chloe_email)

    assert member(client, association["id"], chloe["user_id"])["access_link"] is True


def test_r23_a_manager_revokes_a_members_link(client: Any, new_client: Callable[[], Any]) -> None:
    association, chloe, chloe_email = manager_with_member(client)
    ask_for_link(new_client(), chloe_email)
    token = latest_access_token(chloe_email)
    phone = new_client()
    open_link(phone, token)

    response = client.delete(
        f"/api/associations/{association['id']}/members/{chloe['user_id']}/access-link"
    )

    assert response.status_code == 204
    assert phone.get("/api/session").status_code == 401
    assert open_link(new_client(), token).status_code == 404
    assert member(client, association["id"], chloe["user_id"])["access_link"] is False


def test_manager_revoke_204_when_the_member_has_no_link(client: Any) -> None:
    association, chloe, _ = manager_with_member(client)

    response = client.delete(
        f"/api/associations/{association['id']}/members/{chloe['user_id']}/access-link"
    )

    assert response.status_code == 204


def test_manager_revoke_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    association, chloe, chloe_email = manager_with_member(client)
    ask_for_link(new_client(), chloe_email)
    token = latest_access_token(chloe_email)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    sign_up(bruno, "Bruno", bruno_email)
    add_member(client, association["id"], "Bruno", bruno_email)

    response = bruno.delete(
        f"/api/associations/{association['id']}/members/{chloe['user_id']}/access-link"
    )

    assert response.status_code == 403
    assert "error" in response.json()
    assert open_link(new_client(), token).status_code == 200


def test_manager_revoke_404_when_the_user_is_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, _, _ = manager_with_member(client)
    outsider_email = unique_email("Emma")
    outsider = sign_up(new_client(), "Emma", outsider_email)
    ask_for_link(new_client(), outsider_email)
    token = latest_access_token(outsider_email)

    response = client.delete(
        f"/api/associations/{association['id']}/members/{outsider['id']}/access-link"
    )

    assert response.status_code == 404
    assert "error" in response.json()
    assert open_link(new_client(), token).status_code == 200
