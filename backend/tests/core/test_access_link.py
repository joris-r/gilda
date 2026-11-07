import html
import re
import time
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    ask_for_link,
    break_the_mailer,
    create_account,
    create_association,
    email_count,
    heading,
    latest_access_token,
    latest_email,
    member_line,
    open_link,
    shown,
    sign_in,
    sign_up,
    signed_in_as,
    unique_email,
)

GENERIC = "Something went wrong. Try again."
LINK_INVALID = "This link is no longer valid."
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


def link_sent(email: str) -> str:
    return f"If {email} is known here, a sign-in link has been sent to it."


def signs_in(client: Any, token: str) -> bool:
    """Runs the action of Access link, and tells whether it leads on, signed in."""
    return "window.location" in shown(open_link(client, token))


def assert_invalid_link(text: str) -> None:
    assert LINK_INVALID in text
    assert re.search(r'<a[^>]*href="/sign-in-link"', text)
    assert "window.location" not in text


def revoke_my_link(client: Any) -> Any:
    """Confirms "Revoke my sign-in link", as the dialog does."""
    return client.post("/revoke-access-link")


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
    chloe = add_member(client, association["slug"], "Chloé", chloe_email)
    return association, chloe, chloe_email


def assert_no_email_sent(email: str) -> None:
    time.sleep(0.5)
    assert email_count(email) == 0


class TestSignInLinkForm:
    def test_shows_the_form(self, client: Any) -> None:
        response = client.get("/sign-in-link")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Sign in with an email link"
        assert "Email" in response.text
        assert "Send me a link" in response.text

    def test_links_back_to_sign_in(self, client: Any) -> None:
        page = client.get("/sign-in-link").text

        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Back to Sign in\s*</a>', page)

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert heading(client.get("/sign-in-link")) == "Se connecter par un lien envoyé par e-mail"

    def test_has_the_signed_out_language_selector(self, client: Any) -> None:
        response = client.get("/sign-in-link")

        assert response.status_code == 200
        assert "English" in response.text
        assert "Français" in response.text


class TestSignInLinkSubmit:
    def test_shows_the_message_for_a_known_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)

        assert link_sent(chloe_email) in shown(ask_for_link(new_client(), chloe_email))

    def test_shows_the_same_for_an_unknown_email(self, client: Any) -> None:
        email = unique_email("Nobody")

        assert link_sent(email) in shown(ask_for_link(client, email))

    def test_shows_the_same_when_the_email_cannot_be_sent(
        self, client: Any, new_client: Callable[[], Any], monkeypatch: pytest.MonkeyPatch
    ) -> None:
        _, _, chloe_email = manager_with_member(client)
        break_the_mailer(monkeypatch)

        assert link_sent(chloe_email) in shown(ask_for_link(new_client(), chloe_email))

    def test_the_message_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")
        email = unique_email("Nobody")

        text = shown(ask_for_link(client, email))

        assert f"Si {email} est connu ici, un lien de connexion lui a été envoyé." in text

    def test_the_message_leaves_a_way_back_to_sign_in(self, client: Any) -> None:
        text = shown(ask_for_link(client, unique_email("Nobody")))

        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Back to Sign in\s*</a>', text)

    @pytest.mark.parametrize("signals", [{}, {"email": ""}, {"email": "not-an-email"}])
    def test_a_missing_or_invalid_email_shows_the_generic_error_message(
        self, client: Any, signals: dict[str, str]
    ) -> None:
        assert GENERIC in shown(client.post("/sign-in-link", json=signals))

    def test_a_body_that_is_not_json_shows_the_generic_error_message(self, client: Any) -> None:
        response = client.post(
            "/sign-in-link", content=b"{not json", headers={"content-type": "application/json"}
        )

        assert GENERIC in shown(response)


class TestR24:
    def test_sends_the_access_link_to_a_user_with_a_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)

        ask_for_link(new_client(), email)

        sent = latest_email(email)
        assert sent["Subject"] == ENGLISH["Subject"]
        assert normalized(sent["Text"]).startswith(normalized(ENGLISH["Text"]))
        assert re.search(r"/access\?token=[\w-]+", sent["Text"])

    def test_sends_the_access_link_to_a_member_without_a_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)

        ask_for_link(new_client(), chloe_email)

        latest_access_token(chloe_email)  # raises if no access link was sent

    @pytest.mark.parametrize("accept_language", ["fr", "fr-FR,fr;q=0.9,en;q=0.8"])
    def test_in_french_when_the_browser_prefers_french(
        self, client: Any, new_client: Callable[[], Any], accept_language: str
    ) -> None:
        _, _, chloe_email = manager_with_member(client)

        ask_for_link(new_client(), chloe_email, headers={"Accept-Language": accept_language})

        sent = latest_email(chloe_email)
        assert sent["Subject"] == FRENCH["Subject"]
        assert normalized(sent["Text"]).startswith(normalized(FRENCH["Text"]))
        assert re.search(r"/access\?token=[\w-]+", sent["Text"])

    def test_r20_the_language_cookie_wins_over_the_browser(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)
        browser = new_client()
        browser.cookies.set("language", "fr")

        ask_for_link(browser, chloe_email, headers={"Accept-Language": "en"})

        assert latest_email(chloe_email)["Subject"] == FRENCH["Subject"]

    def test_in_english_otherwise(self, client: Any, new_client: Callable[[], Any]) -> None:
        _, _, chloe_email = manager_with_member(client)

        ask_for_link(new_client(), chloe_email, headers={"Accept-Language": "de"})

        assert latest_email(chloe_email)["Subject"] == ENGLISH["Subject"]

    def test_ignores_the_case_of_the_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)

        ask_for_link(new_client(), chloe_email.upper())

        latest_access_token(chloe_email)

    def test_sends_nothing_to_an_unknown_email(self, client: Any) -> None:
        email = unique_email("Nobody")

        ask_for_link(client, email)

        assert_no_email_sent(email)


def test_r25_a_new_request_sends_the_same_link(client: Any, new_client: Callable[[], Any]) -> None:
    _, _, chloe_email = manager_with_member(client)
    browser = new_client()
    ask_for_link(browser, chloe_email)
    first_token = latest_access_token(chloe_email)
    time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

    ask_for_link(browser, chloe_email)

    assert email_count(chloe_email) == 2
    assert latest_access_token(chloe_email) == first_token
    assert signs_in(new_client(), first_token)


class TestAccessLink:
    def test_the_link_answers_a_page(self, client: Any) -> None:
        response = client.get("/access?token=anything")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")

    def test_fetching_the_link_signs_no_one_in(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)
        browser = new_client()
        ask_for_link(browser, chloe_email)
        token = latest_access_token(chloe_email)

        browser.get(f"/access?token={token}")

        assert signed_in_as(browser) is None
        assert signs_in(browser, token)

    def test_the_page_carries_the_token_safely(self, client: Any) -> None:
        response = client.get("/access", params={"token": "'\"><script>alert(1)</script>"})

        assert response.status_code == 200
        assert "<script>alert(1)</script>" not in html.unescape(response.text)

    def test_signs_a_member_without_a_password_in_and_leads_to_my_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)
        browser = new_client()
        ask_for_link(browser, chloe_email)

        response = open_link(browser, latest_access_token(chloe_email))

        assert "window.location" in shown(response)
        assert "session" in response.headers.get("set-cookie", "")
        assert signed_in_as(browser) == "Chloé"
        assert heading(browser.get("/")) == "My associations"

    def test_signs_a_user_with_a_password_in(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        browser = new_client()
        ask_for_link(browser, email)

        open_link(browser, latest_access_token(email))

        assert signed_in_as(browser) == "Alice"

    def test_signs_in_as_the_links_user_from_another_users_session(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)
        ask_for_link(new_client(), chloe_email)

        assert signs_in(client, latest_access_token(chloe_email))

        assert signed_in_as(client) == "Chloé"

    def test_confirms_the_email(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _, chloe_email = manager_with_member(client)
        browser = new_client()
        ask_for_link(browser, chloe_email)

        open_link(browser, latest_access_token(chloe_email))

        line = member_line(client, association["slug"], chloe_email)
        assert line.startswith(f"Chloé {chloe_email} ")

    def test_lets_a_user_with_an_unconfirmed_email_sign_in_with_their_password(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Bruno")
        create_account(client, "Bruno", email)
        ask_for_link(client, email)

        open_link(client, latest_access_token(email))

        browser = new_client()
        assert "window.location" in shown(sign_in(browser, email))
        assert signed_in_as(browser) == "Bruno"

    def test_stays_usable(self, client: Any, new_client: Callable[[], Any]) -> None:
        _, _, chloe_email = manager_with_member(client)
        ask_for_link(new_client(), chloe_email)
        token = latest_access_token(chloe_email)
        first = new_client()
        open_link(first, token)
        first.post("/sign-out")

        second = new_client()

        assert signs_in(second, token)
        assert signed_in_as(second) == "Chloé"

    def test_r16_replaces_a_session_id_planted_in_the_browser(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        _, _, chloe_email = manager_with_member(client)
        planted = uuid.uuid4().hex
        victim = new_client()
        victim.cookies.set("session", planted)
        attacker = new_client()
        attacker.cookies.set("session", planted)
        ask_for_link(victim, chloe_email)

        response = open_link(victim, latest_access_token(chloe_email))

        assert "window.location" in shown(response)
        assert response.cookies.get("session") not in (None, planted)
        assert signed_in_as(attacker) is None


class TestAccessLinkInvalid:
    def test_unknown_token(self, client: Any) -> None:
        assert_invalid_link(shown(open_link(client, "unknown-token")))
        assert signed_in_as(client) is None

    @pytest.mark.parametrize("signals", [{}, {"token": ""}])
    def test_no_token(self, client: Any, signals: dict[str, str]) -> None:
        assert_invalid_link(shown(client.post("/access", json=signals)))

    def test_revoked_link(self, client: Any, new_client: Callable[[], Any]) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        ask_for_link(client, email)
        token = latest_access_token(email)
        revoke_my_link(client)

        browser = new_client()

        assert_invalid_link(shown(open_link(browser, token)))
        assert signed_in_as(browser) is None

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert "Ce lien n'est plus valide." in shown(open_link(client, "unknown-token"))


# Revoke my sign-in link


def test_r23_revoking_the_link_makes_it_unusable(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)
    chloe = new_client()
    ask_for_link(chloe, chloe_email)
    token = latest_access_token(chloe_email)
    open_link(chloe, token)

    revoke_my_link(chloe)

    assert not signs_in(new_client(), token)


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

    revoke_my_link(laptop)

    assert signed_in_as(phone) is None
    assert signed_in_as(laptop) is None


def test_r23_revoking_the_link_keeps_password_sessions_signed_in(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    ask_for_link(new_client(), email)
    token = latest_access_token(email)
    phone = new_client()
    open_link(phone, token)

    revoke_my_link(client)

    assert signed_in_as(client) == "Alice"
    assert signed_in_as(phone) is None


def test_r25_after_revoking_a_new_request_sends_a_new_link(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    ask_for_link(client, email)
    old_token = latest_access_token(email)
    revoke_my_link(client)
    time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

    ask_for_link(client, email)

    new_token = latest_access_token(email)
    assert new_token != old_token
    assert signs_in(new_client(), new_token)


def test_revoke_my_sign_in_link_shows_it_is_revoked(client: Any) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    ask_for_link(client, email)

    page = shown(revoke_my_link(client))

    assert "Your sign-in link is revoked." in page
    assert "window.location" not in page


def test_revoke_my_sign_in_link_follows_the_language(client: Any) -> None:
    sign_up(client, "Alice")
    client.cookies.set("language", "fr")

    assert "Votre lien de connexion est révoqué." in shown(revoke_my_link(client))


def test_revoke_my_sign_in_link_shows_the_same_without_a_link(client: Any) -> None:
    sign_up(client, "Alice")

    assert "Your sign-in link is revoked." in shown(revoke_my_link(client))


def test_revoke_my_sign_in_link_leads_to_sign_in_from_a_session_opened_with_it(
    client: Any, new_client: Callable[[], Any]
) -> None:
    _, _, chloe_email = manager_with_member(client)
    chloe = new_client()
    ask_for_link(chloe, chloe_email)
    open_link(chloe, latest_access_token(chloe_email))

    page = shown(revoke_my_link(chloe))

    assert "window.location" in page
    assert "Your sign-in link is revoked." not in page
    assert 'type="password"' in chloe.get("/").text


def test_revoke_my_sign_in_link_when_already_signed_out_leads_to_sign_in(client: Any) -> None:
    page = shown(revoke_my_link(client))

    assert "window.location" in page
    assert "Your sign-in link is revoked." not in page
