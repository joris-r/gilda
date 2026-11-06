import html
import re
import time
import uuid
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import pytest

from tests.core.conftest import (
    PASSWORD,
    add_member,
    ask_for_reset,
    break_the_mailer,
    create_account,
    create_association,
    email_count,
    heading,
    latest_email,
    latest_reset_token,
    reset_password,
    run_sql,
    shown,
    sign_up,
    unique_email,
)

NEW_PASSWORD = "battery staple"
GENERIC = "Something went wrong. Try again."
LINK_INVALID = "This link is no longer valid."

ENGLISH = {
    "Subject": "Reset your password",
    "Text": "Choose a new password by opening this link, valid for one hour:",
}
FRENCH = {
    "Subject": "Réinitialisez votre mot de passe",
    "Text": "Choisissez un nouveau mot de passe en ouvrant ce lien, valable une heure :",
}


def link_sent(email: str) -> str:
    return f"If {email} has an account, a reset link has been sent to it."


def reset(client: Any, token: str, password: str = NEW_PASSWORD) -> Any:
    return reset_password(client, token, password)


def can_sign_in(new_client: Callable[[], Any], email: str, password: str) -> bool:
    response = new_client().post("/api/session", json={"email": email, "password": password})
    return bool(response.status_code == 200)


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


def assert_written_in(sent: dict[str, str], language: dict[str, str]) -> None:
    assert sent["Subject"] == language["Subject"]
    assert sent["Text"].startswith(language["Text"])
    assert re.search(r"/reset-password\?token=[\w-]+", sent["Text"])


def assert_invalid_link(text: str) -> None:
    assert LINK_INVALID in text
    assert re.search(r'<a[^>]*href="/forgot-password"', text)


class TestForgotPasswordForm:
    def test_shows_the_form(self, client: Any) -> None:
        response = client.get("/forgot-password")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Forgot your password?"
        assert "Email" in response.text
        assert "Send a reset link" in response.text

    def test_links_back_to_sign_in(self, client: Any) -> None:
        page = client.get("/forgot-password").text

        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Back to Sign in\s*</a>', page)

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert heading(client.get("/forgot-password")) == "Mot de passe oublié ?"

    def test_has_the_signed_out_language_selector(self, client: Any) -> None:
        response = client.get("/forgot-password")

        assert response.status_code == 200
        assert "English" in response.text
        assert "Français" in response.text


class TestForgotPasswordSubmit:
    def test_shows_the_message_for_a_user_with_a_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        response = ask_for_reset(new_client(), email)

        assert link_sent(email) in shown(response)

    def test_shows_the_same_for_an_unknown_email(self, client: Any) -> None:
        email = unique_email("Nobody")

        response = ask_for_reset(client, email)

        assert link_sent(email) in shown(response)

    def test_shows_the_same_for_a_user_without_a_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", chloe_email)

        response = ask_for_reset(new_client(), chloe_email)

        assert link_sent(chloe_email) in shown(response)

    def test_shows_the_same_when_the_email_cannot_be_sent(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        break_the_mailer(monkeypatch)

        response = ask_for_reset(new_client(), email)

        assert link_sent(email) in shown(response)

    def test_the_message_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")
        email = unique_email("Nobody")

        response = ask_for_reset(client, email)

        assert email in shown(response)
        assert link_sent(email) not in shown(response)

    @pytest.mark.parametrize("signals", [{}, {"email": ""}, {"email": "not-an-email"}])
    def test_a_missing_or_invalid_email_shows_the_generic_error_message(
        self, client: Any, signals: dict[str, str]
    ) -> None:
        response = client.post("/forgot-password", json=signals)

        assert GENERIC in shown(response)

    def test_a_body_that_is_not_json_shows_the_generic_error_message(self, client: Any) -> None:
        response = client.post(
            "/forgot-password", content=b"{not json", headers={"content-type": "application/json"}
        )

        assert GENERIC in shown(response)


class TestR21:
    def test_sends_a_reset_link_to_a_user_with_a_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        ask_for_reset(new_client(), email)

        assert_written_in(latest_email(email), ENGLISH)

    @pytest.mark.parametrize("accept_language", ["fr", "fr-FR,fr;q=0.9,en;q=0.8"])
    def test_in_french_when_the_browser_prefers_french(
        self, client: Any, new_client: Callable[[], Any], accept_language: str
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        ask_for_reset(new_client(), email, headers={"Accept-Language": accept_language})

        assert_written_in(latest_email(email), FRENCH)

    def test_r20_the_language_cookie_wins_over_the_browser(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        browser.cookies.set("language", "fr")

        ask_for_reset(browser, email, headers={"Accept-Language": "en"})

        assert_written_in(latest_email(email), FRENCH)

    def test_in_english_otherwise(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        ask_for_reset(new_client(), email, headers={"Accept-Language": "de"})

        assert_written_in(latest_email(email), ENGLISH)

    def test_ignores_the_case_of_the_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        ask_for_reset(new_client(), email.upper())

        latest_reset_token(email)  # raises if no reset email was sent

    def test_sends_a_reset_link_to_a_user_whose_email_is_not_confirmed(self, client: Any) -> None:
        email = unique_email("Bruno")
        create_account(client, "Bruno", email)

        ask_for_reset(client, email)

        latest_reset_token(email)

    def test_sends_nothing_to_a_user_without_a_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", chloe_email)

        ask_for_reset(new_client(), chloe_email)

        assert_no_email_sent(chloe_email)

    def test_sends_nothing_to_an_unknown_email(self, client: Any) -> None:
        email = unique_email("Nobody")

        ask_for_reset(client, email)

        assert_no_email_sent(email)

    def test_r8_a_new_request_invalidates_the_previous_link(
        self, client: Any, new_client: Callable[[], Any]
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
        assert_invalid_link(shown(reset(browser, first_token)))
        assert LINK_INVALID not in shown(reset(browser, second_token))


class TestResetPasswordForm:
    def test_shows_the_form_for_a_valid_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)

        response = browser.get(f"/reset-password?token={latest_reset_token(email)}")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Choose a new password"
        assert "New password" in response.text
        assert 'type="password"' in response.text
        assert "Set password" in response.text
        assert LINK_INVALID not in response.text

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        browser.cookies.set("language", "fr")
        ask_for_reset(browser, email)

        response = browser.get(f"/reset-password?token={latest_reset_token(email)}")

        assert heading(response) == "Choisissez un nouveau mot de passe"

    def test_has_the_signed_out_language_selector(self, client: Any) -> None:
        response = client.get("/reset-password?token=unknown-token")

        assert response.status_code == 200
        assert "English" in response.text
        assert "Français" in response.text

    def test_opening_the_link_leaves_the_token_usable(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)

        browser.get(f"/reset-password?token={token}")

        assert browser.get("/api/session").status_code == 401
        assert LINK_INVALID not in shown(reset(browser, token))
        assert browser.get("/api/session").status_code == 200

    def test_the_page_carries_the_token_safely(self, client: Any) -> None:
        response = client.get("/reset-password", params={"token": '"><script>alert(1)</script>'})

        assert response.status_code == 200
        assert "<script>alert(1)</script>" not in response.text


class TestResetPasswordInvalidLinkWhenOpening:
    def assert_shows_the_message_instead_of_the_form(self, response: Any) -> None:
        assert response.status_code == 200
        assert_invalid_link(response.text)
        assert 'type="password"' not in response.text

    def test_unknown_token(self, client: Any) -> None:
        self.assert_shows_the_message_instead_of_the_form(
            client.get("/reset-password?token=unknown-token")
        )

    def test_no_token(self, client: Any) -> None:
        self.assert_shows_the_message_instead_of_the_form(client.get("/reset-password"))

    def test_expired_token(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)
        expire(token)

        self.assert_shows_the_message_instead_of_the_form(
            browser.get(f"/reset-password?token={token}")
        )

    def test_already_used_token(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)
        reset(browser, token)

        self.assert_shows_the_message_instead_of_the_form(
            new_client().get(f"/reset-password?token={token}")
        )

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        response = client.get("/reset-password?token=unknown-token")

        assert "Ce lien n'est plus valide." in html.unescape(response.text)


class TestResetPasswordInvalidLinkOnSubmit:
    def test_unknown_token(self, client: Any) -> None:
        assert_invalid_link(shown(reset(client, "unknown-token")))
        assert client.get("/api/session").status_code == 401

    def test_no_token(self, client: Any) -> None:
        response = client.post("/reset-password", json={"password": NEW_PASSWORD})

        assert_invalid_link(shown(response))

    def test_expired_token(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)
        assert timedelta(minutes=59) < expires_in(token) <= timedelta(hours=1)
        expire(token)

        assert_invalid_link(shown(reset(browser, token)))
        assert browser.get("/api/session").status_code == 401
        assert can_sign_in(new_client, email, PASSWORD)

    def test_already_used_token(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)
        reset(browser, token)

        assert_invalid_link(shown(reset(new_client(), token, "another password")))
        assert can_sign_in(new_client, email, NEW_PASSWORD)

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert "Ce lien n'est plus valide." in shown(reset(client, "unknown-token"))


class TestR22:
    def test_replaces_the_password(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)

        response = reset(browser, latest_reset_token(email))

        assert LINK_INVALID not in shown(response)
        assert can_sign_in(new_client, email, NEW_PASSWORD)
        assert not can_sign_in(new_client, email, PASSWORD)

    def test_signs_in_and_leads_to_my_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        user = sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)

        response = reset(browser, latest_reset_token(email))

        assert "session" in response.headers.get("set-cookie", "")
        assert browser.get("/api/session").json() == {**user, "superuser": False}
        assert heading(browser.get("/")) == "My associations"

    def test_keeps_the_other_sessions_signed_in(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        user = sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)

        reset(browser, latest_reset_token(email))

        assert client.get("/api/session").json() == {**user, "superuser": False}

    def test_confirms_an_unconfirmed_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        bruno_email = unique_email("Bruno")
        member = add_member(client, association["id"], "Bruno", bruno_email).json()
        bruno = new_client()
        create_account(bruno, "Bruno", bruno_email)
        ask_for_reset(bruno, bruno_email)

        reset(bruno, latest_reset_token(bruno_email))

        assert can_sign_in(new_client, bruno_email, NEW_PASSWORD)
        members = client.get(f"/api/associations/{association['id']}").json()["members"]
        bruno_member = next(m for m in members if m["user_id"] == member["user_id"])
        assert bruno_member["email_verified"] is True

    def test_r16_replaces_a_session_id_planted_in_the_browser(
        self, client: Any, new_client: Callable[[], Any]
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

        assert response.cookies.get("session") not in (None, planted)
        assert attacker.get("/api/session").status_code == 401


class TestResetPasswordInvalidPassword:
    def test_a_short_password_shows_the_generic_error_message_and_the_token_stays_usable(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)

        response = reset(browser, token, "1234567")

        assert GENERIC in shown(response)
        assert browser.get("/api/session").status_code == 401
        assert can_sign_in(new_client, email, PASSWORD)
        assert LINK_INVALID not in shown(reset(browser, token, "12345678"))
        assert can_sign_in(new_client, email, "12345678")

    def test_a_missing_password_shows_the_generic_error_message_and_the_token_stays_usable(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_reset(browser, email)
        token = latest_reset_token(email)

        response = browser.post("/reset-password", json={"token": token})

        assert GENERIC in shown(response)
        assert LINK_INVALID not in shown(reset(browser, token))

    def test_a_body_that_is_not_json_shows_the_generic_error_message(self, client: Any) -> None:
        response = client.post(
            "/reset-password", content=b"{not json", headers={"content-type": "application/json"}
        )

        assert GENERIC in shown(response)


class TestEndpointsRemoved:
    @pytest.mark.parametrize(
        "path", ["/api/accounts/password-reset", "/api/accounts/password-reset/confirm"]
    )
    def test_answers_404(self, client: Any, path: str) -> None:
        assert client.post(path, json={}).status_code == 404
