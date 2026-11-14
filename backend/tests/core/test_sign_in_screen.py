import re
import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    PASSWORD,
    add_member,
    create_account,
    create_association,
    latest_verification_token,
    shown,
    sign_up,
    signed_in_as,
    unique_email,
)

WRONG_EN = "Wrong email or password."
WRONG_FR = "E-mail ou mot de passe incorrect."


def heading(response: Any) -> str:
    match = re.search(r"<h1[^>]*>\s*(.*?)\s*</h1>", response.text, re.DOTALL)
    assert match, f"no heading in {response.text}"
    return match.group(1)


def sign_in(client: Any, email: str, password: str = PASSWORD, **kwargs: Any) -> Any:
    return client.post("/sign-in", json={"email": email, "password": password}, **kwargs)


def assert_is_event_stream(response: Any) -> None:
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/event-stream")


class TestSignIn:
    # /core/ui/sign-in/form
    def test_signed_out_slash_shows_the_form(self, client: Any) -> None:
        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Sign in"
        assert "Email" in response.text
        assert "Password" in response.text
        assert 'type="password"' in response.text

    # /core/ui/sign-in/create
    # /core/ui/sign-in/forgot
    # /core/ui/sign-in/link
    @pytest.mark.parametrize(
        ("text", "path"),
        [
            ("Create an account", "/signup"),
            ("Forgot your password?", "/forgot-password"),
            ("Sign in with an email link", "/sign-in-link"),
        ],
    )
    def test_links(self, client: Any, text: str, path: str) -> None:
        page = client.get("/").text

        assert re.search(rf'<a[^>]*href="{path}"[^>]*>\s*{re.escape(text)}\s*</a>', page)

    # /core/ui/sign-in/wrong
    def test_shows_no_wrong_credentials_message_until_submitted(self, client: Any) -> None:
        assert WRONG_EN not in client.get("/").text

    # /core/ui/header/signed-out
    def test_signed_out_header_has_the_language_selector(self, client: Any) -> None:
        page = client.get("/").text

        assert "English" in page
        assert "Français" in page

    # /core/ui/sign-in/wrong
    # /core/operations/sign-in/wrong
    def test_wrong_password_shows_the_message(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)

        response = sign_in(client, email, "not the password")

        assert_is_event_stream(response)
        assert WRONG_EN in response.text
        assert heading(client.get("/")) == "Sign in"

    # /core/ui/sign-in/wrong
    # /core/operations/sign-in/wrong
    def test_unknown_email_shows_the_same_message(self, client: Any) -> None:
        response = sign_in(client, unique_email("Nobody"))

        assert_is_event_stream(response)
        assert WRONG_EN in response.text

    # /core/ui/sign-in/wrong
    # /core/operations/sign-in/wrong
    def test_unconfirmed_email_shows_the_same_message(self, client: Any) -> None:
        email = unique_email("Alice")
        assert email in create_account(client, "Alice", email).text
        latest_verification_token(email)

        response = sign_in(client, email)

        assert_is_event_stream(response)
        assert WRONG_EN in response.text
        assert heading(client.get("/")) == "Sign in"

    # /core/ui/sign-in/wrong
    # /core/ui/header/language
    def test_wrong_credentials_message_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        response = sign_in(client, unique_email("Nobody"))

        assert WRONG_FR in response.text

    # /core/ui/sign-in/signed-in
    # /core/operations/sign-in/signed-in
    # /core/ui/sign-in/sign-in
    def test_success_signs_in_and_leads_to_slash(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)

        response = sign_in(client, email)

        assert_is_event_stream(response)
        assert WRONG_EN not in response.text
        assert heading(client.get("/")) == "My associations"

    # /core/model/session/id
    def test_two_browsers_signed_in_as_one_user_get_different_session_ids(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        other = new_client()

        sign_in(other, email)

        assert other.cookies["session"] != client.cookies["session"]
        assert signed_in_as(other) == "Alice"
        assert signed_in_as(client) == "Alice"

    # /core/operations/sign-in/new-session
    def test_a_new_session_id_replaces_the_previous_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(client, "Alice", email)
        previous = client.cookies["session"]

        sign_in(client, email)

        assert client.cookies["session"] != previous
        stale = new_client()
        stale.cookies.set("session", previous)
        assert heading(stale.get("/")) == "Sign in"

    # /core/operations/sign-in/new-session
    def test_replaces_a_session_id_planted_in_the_browser(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)
        planted = uuid.uuid4().hex
        client.cookies.set("session", planted)
        attacker = new_client()
        attacker.cookies.set("session", planted)

        response = sign_in(client, email)

        assert "window.location" in shown(response)
        assert response.cookies.get("session") not in (None, planted)
        assert signed_in_as(client) == "Alice"
        assert signed_in_as(attacker) is None

    # /core/operations/sign-in/new-session
    def test_replaces_the_id_of_an_existing_session(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)
        attacker = new_client()
        sign_up(attacker, "Mallory")
        planted = attacker.cookies.get("session")
        client.cookies.set("session", planted)

        response = sign_in(client, email)

        assert "window.location" in shown(response)
        assert response.cookies.get("session") not in (None, planted)
        assert signed_in_as(client) == "Alice"
        assert signed_in_as(attacker) is None

    # /core/operations/sign-in/signed-in
    # /core/model/user/email
    def test_ignores_the_case_of_the_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)

        response = sign_in(client, email.upper())

        assert WRONG_EN not in shown(response)
        assert signed_in_as(client) == "Alice"

    # /core/ui/sign-in/wrong
    # /core/operations/sign-in/wrong
    def test_a_member_added_without_a_password_shows_the_same_message(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        manager = new_client()
        sign_up(manager, "Alice")
        association = create_association(manager)
        email = unique_email("Chloe")
        add_member(manager, association["slug"], "Chloé", email)

        response = sign_in(client, email)

        assert WRONG_EN in shown(response)
        assert signed_in_as(client) is None
