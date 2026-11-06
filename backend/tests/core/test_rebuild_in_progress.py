from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import sign_up, unique_email


class TestTemporarySlash:
    def test_signed_in_shows_my_associations_the_user_and_sign_out(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = client.get("/").text

        assert "My associations" in page
        assert "Alice" in page
        assert "Sign out" in page
        assert 'type="password"' not in page

    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = client.get("/").text

        assert "Mes associations" in page
        assert "Se déconnecter" in page

    def test_escapes_the_display_name(self, client: Any) -> None:
        sign_up(client, "<b>Alice</b>", unique_email("Alice"))

        page = client.get("/").text

        assert "<b>Alice</b>" not in page
        assert "&lt;b&gt;Alice&lt;/b&gt;" in page

    def test_sign_out_leads_to_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        sign_up(client, "Alice")
        session = client.cookies["session"]

        response = client.post("/sign-out")

        assert response.status_code == 200, response.text
        assert response.headers["content-type"].startswith("text/event-stream")
        assert 'type="password"' in client.get("/").text
        stale = new_client()
        stale.cookies.set("session", session)
        assert 'type="password"' in stale.get("/").text


class TestOtherPaths:
    @pytest.mark.parametrize(
        "path",
        [
            "/signup",
            "/forgot-password",
            "/sign-in-link",
            "/access?token=x",
            "/reset-password?token=x",
            "/verify-email?token=x",
            "/associations/new",
            "/association/jardin/members",
        ],
    )
    def test_any_other_path_answers_404(self, client: Any, path: str) -> None:
        assert client.get(path).status_code == 404


class TestJsonApi:
    def test_stays_available(self, client: Any) -> None:
        user = sign_up(client, "Alice")

        response = client.get("/api/associations")

        assert user["display_name"] == "Alice"
        assert response.status_code == 200
        assert response.json() == []

    def test_unknown_api_path_answers_json_404(self, client: Any) -> None:
        response = client.get("/api/nothing-here")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
