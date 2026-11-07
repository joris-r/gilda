import html
import re
import uuid
from collections.abc import Callable
from datetime import date, timedelta
from typing import Any

import pytest

from tests.core.conftest import heading, sign_up, unique_email


def part(page: str, tag: str) -> str:
    match = re.search(rf"<{tag}[ >].*</{tag}>", page, re.DOTALL)
    assert match, f"no {tag} in {page}"
    return match.group(0)


class TestMyAssociationsHeader:
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


class TestOtherPaths:
    @pytest.mark.parametrize(
        "path",
        [
            "/associations/new",
            "/association/jardin/schedule",
        ],
    )
    def test_any_other_path_answers_the_not_found_page(self, client: Any, path: str) -> None:
        response = client.get(path)

        assert response.status_code == 404
        assert "Page not found" in response.text


class TestScheduleSettings:
    def test_shows_its_sections(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = f"a-{uuid.uuid4().hex[:12]}"
        created = client.post("/api/associations", json={"name": "Jardin", "slug": slug})
        assert created.status_code == 201

        response = client.get(f"/association/{slug}/settings")

        assert response.status_code == 200
        main = html.unescape(part(response.text, "main"))
        for present in [
            "Planning period",
            "Closures",
            "Add a closure",
            "Slots",
            "Add a slot",
            "Share link",
            "Create a share link",
            "Members' preferences",
        ]:
            assert present in main


class TestMyAvailability:
    def test_shows_its_my_preferences_absences_and_note_sections(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = f"a-{uuid.uuid4().hex[:12]}"
        created = client.post("/api/associations", json={"name": "Jardin", "slug": slug})
        assert created.status_code == 201

        response = client.get(f"/association/{slug}/availability")

        assert response.status_code == 200
        main = html.unescape(part(response.text, "main"))
        for present in ["My preferences", "Absences", "Add an absence", "Note for the managers"]:
            assert present in main


class TestSchedule:
    def test_shows_its_weeks_and_menus_with_the_managers_part(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = f"a-{uuid.uuid4().hex[:12]}"
        created = client.post("/api/associations", json={"name": "Jardin", "slug": slug})
        assert created.status_code == 201
        slot = {"weekday": "thursday", "start": "10:00", "end": "13:00"}
        added = client.post(f"/api/associations/{created.json()['id']}/slots", json=slot)
        assert added.status_code == 201

        response = client.get(f"/association/{slug}")

        assert response.status_code == 200
        page = html.unescape(response.text)
        for present in ["Week", "More weeks", "My availability", "Members", "Schedule settings"]:
            assert present in page
        today = date.today()
        thursday = today + timedelta(days=(3 - today.weekday()) % 7 + 7)
        menu = client.post(
            f"/association/{slug}/menu",
            json={"date": thursday.isoformat(), "start": "10:00", "end": "13:00"},
        )
        assert menu.status_code == 200
        text = html.unescape(menu.text)
        assert "Sign up" in text
        assert re.search(r"<li[ >].*?\bAlice\b.*?</li>", text, re.DOTALL)


class TestNotFound:
    @pytest.mark.parametrize("path", ["/nothing-here", "/static/nothing-here.css", "/a/b/c"])
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
        assert client.get("/api/session").status_code == 200

    def test_follows_the_language(self, client: Any) -> None:
        client.cookies.set("language", "fr")

        assert "Page introuvable" in client.get("/nothing-here").text

    def test_follows_the_browser_language(self, client: Any) -> None:
        page = client.get("/nothing-here", headers={"Accept-Language": "fr"}).text

        assert "Page introuvable" in page
        assert "Retour à la page d'accueil" in html.unescape(page)


class TestJsonApi:
    def test_stays_available(self, client: Any) -> None:
        user = sign_up(client, "Alice")

        response = client.get("/api/session")

        assert response.status_code == 200
        assert response.json()["display_name"] == user["display_name"]

    def test_get_api_associations_answers_nothing(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get("/api/associations")

        assert response.status_code in (404, 405)

    def test_unknown_api_path_answers_json_404(self, client: Any) -> None:
        response = client.get("/api/nothing-here")

        assert response.status_code == 404
        assert response.headers["content-type"].startswith("application/json")
