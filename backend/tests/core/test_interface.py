import html
import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    create_association,
    heading,
    names_listed,
    sign_up,
    signed_in_as,
    unique_email,
    unique_slug,
)

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def part(page: str, tag: str) -> str:
    match = re.search(rf"<{tag}[ >].*</{tag}>", page, re.DOTALL)
    assert match, f"no {tag} in {page}"
    return match.group(0)


class TestHeader:
    def test_signed_in_shows_my_associations_the_user_and_sign_out(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = client.get("/").text

        assert heading(client.get("/")) == "My associations"
        assert "Alice" in page
        assert "Sign out" in page
        assert 'type="password"' not in page

    def test_header_location_shows_my_associations_in_place_of_a_title(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = client.get("/").text

        assert "My associations" in part(page, "header")
        assert "My associations" not in part(page, "main")

    def test_the_menu_has_the_language_selector_revoke_delete_my_account_and_sign_out(
        self, client: Any
    ) -> None:
        sign_up(client, "Alice")

        page = client.get("/").text

        assert "Français" in page
        assert "Revoke my sign-in link" in page
        assert "Delete my account" in page
        assert "Sign out" in page

    def test_revoke_my_sign_in_link_asks_for_confirmation(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = html.unescape(client.get("/").text)

        assert "Revoke your sign-in link? Sessions opened with it are signed out." in page
        assert re.search(r"<button[^>]*>\s*Confirm\s*</button>", page)

    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = client.get("/").text

        assert "Mes associations" in part(page, "header")
        assert "Se déconnecter" in page
        assert "Révoquer mon lien de connexion" in page
        assert "Supprimer mon compte" in page

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


class TestNotFound:
    @pytest.mark.parametrize(
        "path",
        [
            "/nothing-here",
            "/static/nothing-here.css",
            "/a/b/c",
            "/associations/new",
            "/association/jardin/schedule",
        ],
    )
    def test_answers_an_html_page(self, client: Any, path: str) -> None:
        response = client.get(path)

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")
        assert re.search(r"<h1[^>]*>\s*Page not found\s*</h1>", response.text)

    @pytest.mark.parametrize(
        "path",
        [
            "/sign-in",
            "/sign-out",
            "/delete-account",
            "/revoke-access-link",
            "/language",
            "/signup/resend",
            "/association/jardin/rename",
            "/association/jardin/identifier",
            "/association/jardin/delete",
            "/association/jardin/settings/slots",
            "/association/jardin/settings/period",
            "/association/jardin/settings/period/clear",
            "/association/jardin/settings/closures",
            "/association/jardin/settings/preferences/00000000-0000-4000-8000-000000000000"
            "/00000000-0000-4000-8000-000000000000",
            "/association/jardin/availability/preferences/00000000-0000-4000-8000-000000000000",
            "/association/jardin/availability/absences",
            "/association/jardin/availability/note",
            "/association/jardin/weeks",
            "/association/jardin/settings/share-link",
            "/association/jardin/settings/share-link/revoke",
            "/shared/Hq3v/weeks",
            "/association/jardin/summary/00000000-0000-4000-8000-000000000000/confirm",
            "/association/jardin/summary/00000000-0000-4000-8000-000000000000/cancel",
        ],
    )
    def test_a_path_only_actions_use_answers_it_too(self, client: Any, path: str) -> None:
        response = client.get(path)

        assert response.status_code == 404
        assert "Page not found" in response.text

    def test_leads_to_the_home_page(self, client: Any) -> None:
        page = client.get("/nothing-here").text

        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Back to the home page\s*</a>', page)

    def test_has_the_signed_out_header(self, client: Any) -> None:
        page = client.get("/nothing-here").text

        assert "English" in page
        assert "Français" in page

    def test_signed_in_shows_the_same_and_stays_signed_in(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get("/nothing-here")

        assert response.status_code == 404
        assert "Page not found" in response.text
        assert "Sign out" not in response.text
        assert signed_in_as(client) == "Alice"

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert "Page introuvable" in client.get("/nothing-here").text

    def test_follows_the_browser_language(self, client: Any) -> None:
        page = client.get("/nothing-here", headers={"Accept-Language": "fr"}).text

        assert "Page introuvable" in page
        assert "Retour à la page d'accueil" in html.unescape(page)

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("POST", "/api/session"),
            ("GET", "/api/session"),
            ("DELETE", "/api/session"),
            ("POST", "/api/session/access-link"),
            ("DELETE", "/api/access-link"),
            ("POST", "/api/accounts"),
            ("DELETE", "/api/accounts/me"),
            ("POST", "/api/accounts/verify"),
            ("POST", "/api/accounts/verify/resend"),
            ("POST", "/api/accounts/password-reset"),
            ("POST", "/api/accounts/password-reset/confirm"),
            ("GET", "/api/associations"),
            ("POST", "/api/associations"),
            ("GET", "/api/associations/by-slug/jardin"),
            ("GET", f"/api/associations/{UNKNOWN_ID}"),
            ("PATCH", f"/api/associations/{UNKNOWN_ID}"),
            ("DELETE", f"/api/associations/{UNKNOWN_ID}"),
            ("POST", f"/api/associations/{UNKNOWN_ID}/members"),
            ("POST", f"/api/associations/{UNKNOWN_ID}/members/{UNKNOWN_ID}/access-link"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/slots"),
            ("POST", f"/api/associations/{UNKNOWN_ID}/slots"),
            ("PUT", f"/api/associations/{UNKNOWN_ID}/slots/{UNKNOWN_ID}"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/closures"),
            ("POST", f"/api/associations/{UNKNOWN_ID}/closures"),
            ("DELETE", f"/api/associations/{UNKNOWN_ID}/closures/{UNKNOWN_ID}"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/planning-period"),
            ("PUT", f"/api/associations/{UNKNOWN_ID}/planning-period"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/preferences"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/absences"),
            ("POST", f"/api/associations/{UNKNOWN_ID}/absences"),
            ("PUT", f"/api/associations/{UNKNOWN_ID}/absences/{UNKNOWN_ID}"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/note"),
            ("PUT", f"/api/associations/{UNKNOWN_ID}/note"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/member-absences"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/notes"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/registration-counts"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/schedule"),
            ("POST", f"/api/associations/{UNKNOWN_ID}/registrations"),
            ("PATCH", f"/api/associations/{UNKNOWN_ID}/registrations/{UNKNOWN_ID}"),
            ("GET", f"/api/associations/{UNKNOWN_ID}/share-link"),
            ("GET", "/api/shared/Hq3v"),
            ("GET", "/api/shared/Hq3v/schedule"),
            ("GET", "/api/nothing-here"),
        ],
    )
    def test_the_former_json_api_paths_answer_it_signed_in(
        self, client: Any, method: str, path: str
    ) -> None:
        sign_up(client, "Alice")

        response = client.request(method, path, json={})

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("text/html")
        assert re.search(r"<h1[^>]*>\s*Page not found\s*</h1>", response.text)

    def test_a_former_json_api_creation_creates_nothing(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()

        response = client.post("/api/associations", json={"name": "Jardin", "slug": slug})

        assert response.status_code == 404
        assert names_listed(client) == []

    def test_a_former_json_api_write_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        association = create_association(client)
        bruno = new_client()
        bruno_email = unique_email("Bruno")
        sign_up(bruno, "Bruno", bruno_email)

        response = client.post(
            f"/api/associations/{association['id']}/members",
            json={"display_name": "Bruno", "email": bruno_email, "role": "volunteer"},
        )

        assert response.status_code == 404
        assert names_listed(bruno) == []
