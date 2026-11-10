import html
import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    create_association,
    delete_association,
    listed,
    names_listed,
    shown,
    sign_up,
    unique_email,
    unique_slug,
)

NAME = "Jardin partagé des Lilas"
GENERIC = "Something went wrong. Try again."
MALFORMED_EN = (
    "Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit."
)
MALFORMED_FR = (
    "Utilisez uniquement des lettres minuscules, des chiffres et des tirets, "
    "en commençant et en finissant par une lettre ou un chiffre."
)
TAKEN_EN = "This association identifier is already taken."
TAKEN_FR = "Cet identifiant d'association est déjà pris."
FR_NONE = "Vous n'êtes membre d'aucune association."


def part(page: str, tag: str) -> str:
    match = re.search(rf"<{tag}[ >].*</{tag}>", page, re.DOTALL)
    assert match, f"no {tag} in {page}"
    return match.group(0)


def text_of(fragment: str) -> str:
    """What a piece of HTML shows, without its tags and attributes."""
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def line_of(page: str, name: str) -> str:
    """What the association named `name` shows outside its registrations."""
    items = listed(part(page, "main"))
    found = [item.text for item in items if item.name == name]
    assert len(found) == 1, f"{name} in {items}"
    return found[0]


def create_on_screen(client: Any, name: str, slug: str) -> Any:
    """Submits New association, as the screen does."""
    return client.post("/association/new", json={"name": name, "slug": slug})


def my_associations(client: Any) -> str:
    response = client.get("/")
    assert response.status_code == 200
    return str(response.text)


def new_association(client: Any) -> str:
    response = client.get("/association/new")
    assert response.status_code == 200
    return str(response.text)


class TestMyAssociations:
    # /home/ui/my-associations/list
    # /home/operations/list-my-associations/listed
    def test_shows_each_association_with_the_users_role(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        alice = sign_up(client, "Alice")
        create_association(client, NAME)
        bruno = new_client()
        bruno_email = unique_email("Bruno")
        sign_up(bruno, "Bruno", bruno_email)
        theirs = create_association(bruno, "Repair Café Belleville")
        add_member(bruno, theirs["slug"], "Alice", alice["email"])

        page = my_associations(client)

        assert "manager" in line_of(page, NAME).lower()
        assert "volunteer" in line_of(page, "Repair Café Belleville").lower()

    # /home/ui/my-associations/list
    # /core/ui/header/language
    def test_roles_follow_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        alice = sign_up(client, "Alice")
        create_association(client, NAME)
        bruno = new_client()
        sign_up(bruno, "Bruno", unique_email("Bruno"))
        theirs = create_association(bruno, "Repair Café Belleville")
        add_member(bruno, theirs["slug"], "Alice", alice["email"])
        client.cookies.set("language", "fr")

        page = my_associations(client)

        assert "responsable" in line_of(page, NAME).lower()
        assert "bénévole" in line_of(page, "Repair Café Belleville").lower()

    # /home/operations/list-my-associations/listed
    def test_shows_only_the_users_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        bruno = new_client()
        sign_up(bruno, "Bruno", unique_email("Bruno"))
        create_association(bruno, "Repair Café Belleville")

        assert "Repair Café Belleville" not in my_associations(client)

    # /home/ui/my-associations/list
    def test_each_name_leads_to_the_associations_schedule(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()
        create_association(client, NAME, slug)

        page = html.unescape(my_associations(client))

        assert re.search(rf'<a[^>]*href="/association/{slug}"[^>]*>\s*{NAME}\s*</a>', page)

    # /home/ui/my-associations/none
    def test_with_no_association_shows_the_message(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = my_associations(client)

        assert "You are not a member of any association yet." in part(page, "main")

    # /home/ui/my-associations/none
    def test_with_an_association_does_not_show_the_message(self, client: Any) -> None:
        sign_up(client, "Alice")
        create_association(client, NAME)

        assert "You are not a member of any association yet." not in my_associations(client)

    # /home/ui/my-associations/none
    # /home/ui/my-associations/new
    # /core/ui/header/language
    def test_the_message_and_new_association_follow_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = text_of(part(my_associations(client), "main"))

        assert FR_NONE in page
        assert "Nouvelle association" in page

    # /home/ui/my-associations/new
    @pytest.mark.parametrize("with_association", [False, True])
    def test_new_association_leads_to_its_screen(self, client: Any, with_association: bool) -> None:
        sign_up(client, "Alice")
        if with_association:
            create_association(client, NAME)

        page = part(my_associations(client), "main")

        link = re.search(r'<a[^>]*href="/association/new"[^>]*>(.*?)</a>', page, re.DOTALL)
        assert link, page
        assert re.fullmatch(r"\s*\+\s*New association\s*", text_of(link.group(1)))

    def test_escapes_the_association_name(self, client: Any) -> None:
        sign_up(client, "Alice")
        create_association(client, "<b>Lilas</b>")

        page = my_associations(client)

        assert "<b>Lilas</b>" not in page
        assert "&lt;b&gt;Lilas&lt;/b&gt;" in page


class TestNewAssociationScreen:
    # /core/ui/new-association/form
    def test_shows_the_form(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = part(new_association(client), "main")

        assert re.search(r"<h1[^>]*>\s*New association\s*</h1>", page)
        assert re.search(r"<label[^>]*>\s*Name\b", page)
        assert re.search(r"<label[^>]*>\s*Association identifier\b", page)
        assert "/association/" in text_of(page)
        assert re.search(r"<button[^>]*>\s*Create association\s*</button>", page)

    # /core/ui/new-association/cancel
    def test_cancel_leads_to_my_associations(self, client: Any) -> None:
        sign_up(client, "Alice")

        page = part(new_association(client), "main")

        assert re.search(r'<a[^>]*href="/"[^>]*>\s*Cancel\s*</a>', page)

    # /core/ui/header/location
    # /core/ui/header/menu
    def test_header_location_leads_to_my_associations_then_names_the_screen(
        self, client: Any
    ) -> None:
        sign_up(client, "Alice")

        header = part(new_association(client), "header")

        assert re.search(r'<a[^>]*href="/"[^>]*>\s*My associations\s*</a>', header)
        assert "New association" in text_of(header)
        assert "Alice" in header

    # /core/ui/header/location
    # /core/ui/new-association/form
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = new_association(client)

        assert "Mes associations" in part(page, "header")
        assert "Nouvelle association" in part(page, "main")

    # /core/ui/access/signed-out
    def test_signed_out_shows_sign_in(self, client: Any) -> None:
        response = client.get("/association/new")

        assert response.status_code == 200
        assert 'type="password"' in response.text


class TestCreating:
    # /core/operations/create-association/created
    # /core/ui/new-association/create
    def test_makes_the_user_its_manager(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()

        shown(create_on_screen(client, NAME, slug))

        assert names_listed(client) == [NAME]
        assert f'href="/association/{slug}"' in my_associations(client)
        assert "manager" in line_of(my_associations(client), NAME).lower()

    # /core/ui/new-association/created
    def test_leads_to_the_new_associations_schedule(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()

        text = shown(create_on_screen(client, NAME, slug))

        assert "window.location" in text
        assert f"/association/{slug}" in text

    # /core/ui/new-association/malformed
    # /core/operations/create-association/malformed-slug
    # /core/model/association/slug-format
    @pytest.mark.parametrize(
        "slug",
        ["Jardin", "jardin lilas", "jardin_lilas", "-jardin", "jardin-", "jardín", "a" * 51],
    )
    def test_a_malformed_slug_shows_its_message(self, client: Any, slug: str) -> None:
        sign_up(client, "Alice")

        text = shown(create_on_screen(client, NAME, slug))

        assert MALFORMED_EN in text
        assert "window.location" not in text
        assert names_listed(client) == []

    # /core/model/association/slug-format
    @pytest.mark.parametrize("slug", ["a", "7", "2-jardins", "jardin-des-lilas"])
    def test_a_well_formed_slug_is_not_refused_as_malformed(self, client: Any, slug: str) -> None:
        sign_up(client, "Alice")

        text = shown(create_on_screen(client, NAME, slug))

        # These fixed slugs may be held already, by another test or an earlier run.
        assert MALFORMED_EN not in text
        assert f"/association/{slug}" in text or TAKEN_EN in text

    # /core/model/association/slug-format
    # /core/operations/create-association/created
    def test_accepts_a_slug_of_50_characters(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug().ljust(50, "x")

        text = shown(create_on_screen(client, NAME, slug))

        assert f"/association/{slug}" in text
        assert names_listed(client) == [NAME]

    # /core/operations/create-association/created
    # /core/operations/delete-association/deleted
    def test_accepts_the_slug_of_a_deleted_association(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()
        create_association(client, NAME, slug)
        assert "window.location" in shown(delete_association(client, slug))

        text = shown(create_on_screen(client, "Repair Café", slug))

        assert f"/association/{slug}" in text
        assert names_listed(client) == ["Repair Café"]

    # /core/ui/new-association/taken
    # /core/operations/create-association/taken
    def test_a_taken_slug_shows_its_message(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()
        create_association(client, NAME, slug)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        text = shown(create_on_screen(other, "Repair Café", slug))

        assert TAKEN_EN in text
        assert "window.location" not in text
        assert names_listed(other) == []

    # /core/ui/new-association/taken
    # /core/operations/create-association/taken
    def test_the_slug_new_shows_the_taken_message(self, client: Any) -> None:
        sign_up(client, "Alice")

        assert TAKEN_EN in shown(create_on_screen(client, NAME, "new"))
        assert names_listed(client) == []

    # /core/ui/new-association/malformed
    # /core/ui/new-association/taken
    # /core/ui/header/language
    def test_messages_follow_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        slug = unique_slug()
        create_association(client, NAME, slug)
        client.cookies.set("language", "fr")

        assert MALFORMED_FR in shown(create_on_screen(client, NAME, "Jardin"))
        assert TAKEN_FR in shown(create_on_screen(client, NAME, slug))

    # /core/model/association/name
    # /core/model/association/slug-format
    # /core/operations/general/refused
    @pytest.mark.parametrize(
        "body",
        [
            {"name": "", "slug": "a-slug"},
            {"slug": "a-slug"},
            {"name": NAME, "slug": ""},
            {"name": NAME},
            {"name": 7, "slug": "a-slug"},
        ],
    )
    def test_a_missing_field_saves_nothing(self, client: Any, body: dict[str, Any]) -> None:
        sign_up(client, "Alice")
        if body.get("slug"):
            body = {**body, "slug": unique_slug()}

        text = shown(client.post("/association/new", json=body))

        assert "window.location" not in text
        assert names_listed(client) == []

    # /ui/errors/generic
    # /core/model/association/name
    def test_an_empty_name_shows_the_generic_error_message(self, client: Any) -> None:
        sign_up(client, "Alice")

        assert GENERIC in shown(create_on_screen(client, "", unique_slug()))

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_creates_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        slug = unique_slug()

        text = shown(create_on_screen(client, NAME, slug))

        assert "window.location" in text
        assert f"/association/{slug}" not in text
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))
        assert create_association(other, NAME, slug)["slug"] == slug
