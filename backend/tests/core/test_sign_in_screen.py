import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import PASSWORD, latest_verification_token, sign_up, unique_email

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
    def test_signed_out_slash_shows_the_form(self, client: Any) -> None:
        response = client.get("/")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/html")
        assert heading(response) == "Sign in"
        assert "Email" in response.text
        assert "Password" in response.text
        assert 'type="password"' in response.text

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

    def test_shows_no_wrong_credentials_message_until_submitted(self, client: Any) -> None:
        assert WRONG_EN not in client.get("/").text

    def test_signed_out_header_has_the_language_selector(self, client: Any) -> None:
        page = client.get("/").text

        assert "English" in page
        assert "Français" in page

    def test_wrong_password_shows_the_message(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)

        response = sign_in(client, email, "not the password")

        assert_is_event_stream(response)
        assert WRONG_EN in response.text
        assert heading(client.get("/")) == "Sign in"

    def test_unknown_email_shows_the_same_message(self, client: Any) -> None:
        response = sign_in(client, unique_email("Nobody"))

        assert_is_event_stream(response)
        assert WRONG_EN in response.text

    def test_unconfirmed_email_shows_the_same_message(self, client: Any) -> None:
        email = unique_email("Alice")
        created = client.post(
            "/api/accounts",
            json={"display_name": "Alice", "email": email, "password": PASSWORD},
        )
        assert created.status_code == 201
        latest_verification_token(email)

        response = sign_in(client, email)

        assert_is_event_stream(response)
        assert WRONG_EN in response.text
        assert heading(client.get("/")) == "Sign in"

    def test_wrong_credentials_message_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        response = sign_in(client, unique_email("Nobody"))

        assert WRONG_FR in response.text

    def test_success_signs_in_and_leads_to_slash(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        email = unique_email("Alice")
        sign_up(new_client(), "Alice", email)

        response = sign_in(client, email)

        assert_is_event_stream(response)
        assert WRONG_EN not in response.text
        assert heading(client.get("/")) == "My associations"

    def test_r16_a_new_session_id_replaces_the_previous_one(
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
