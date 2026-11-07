import html
import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    ask_for_link,
    change_role,
    confirm_email,
    create_account,
    create_association,
    latest_access_token,
    latest_verification_token,
    open_link,
    remove_member,
    shown,
    sign_up,
    unique_email,
    unique_slug,
)

NAME = "Jardin partagé des Lilas"
GENERIC = "Something went wrong. Try again."
UNKNOWN = "This association does not exist or you are not a member."
NOT_JOINED = "not joined yet"
LAST_MANAGER = "An association keeps at least one manager."


def part(page: str, tag: str) -> str:
    match = re.search(rf"<{tag}[ >].*</{tag}>", page, re.DOTALL)
    assert match, f"no {tag} in {page}"
    return match.group(0)


def text_of(fragment: str) -> str:
    """What a piece of HTML shows, without its tags and attributes."""
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def lines(page: str) -> list[str]:
    """The text of each list item of main, in order."""
    return [text_of(item) for item in re.findall(r"<li.*?</li>", part(page, "main"), re.DOTALL)]


def line_of(page: str, name: str) -> str:
    """The text of the list item that shows `name`."""
    found = [line for line in lines(page) if name in line]
    assert len(found) == 1, f"{name} in {lines(page)}"
    return found[0]


def members_page(client: Any, slug: str) -> str:
    response = client.get(f"/association/{slug}/members")
    assert response.status_code == 200
    return str(response.text)


def add_on_screen(
    client: Any, slug: str, display_name: str, email: str, role: str = "volunteer"
) -> Any:
    """Submits Add a member, as the screen does."""
    return client.post(
        f"/association/{slug}/members",
        json={"displayName": display_name, "email": email, "role": role},
    )


def member_count(client: Any, association: dict[str, Any]) -> int:
    members = client.get(f"/api/associations/{association['id']}").json()["members"]
    return len(members)


def user_id(client: Any, association: dict[str, Any], display_name: str) -> str:
    """The user ID of the member `display_name`, as the API lists it."""
    members = client.get(f"/api/associations/{association['id']}").json()["members"]
    found: str = next(m["user_id"] for m in members if m["display_name"] == display_name)
    return found


def role_of(client: Any, association: dict[str, Any], display_name: str) -> str:
    """The role that Members shows for `display_name`, in lowercase."""
    return line_of(members_page(client, association["slug"]), display_name).lower()


def managed(client: Any, name: str = NAME) -> dict[str, Any]:
    """Alice signs up and creates an association, which she manages."""
    sign_up(client, "Alice")
    return create_association(client, name, unique_slug())


def with_volunteer(client: Any, new_client: Callable[[], Any]) -> tuple[dict[str, Any], Any]:
    """Alice manages an association; Bruno, signed in on his own client, volunteers in it."""
    association = managed(client)
    bruno = new_client()
    email = unique_email("Bruno")
    sign_up(bruno, "Bruno", email)
    assert add_member(client, association["id"], "Bruno", email).status_code == 201
    return association, bruno


class TestMembers:
    def test_shows_each_member_with_email_and_role(self, client: Any) -> None:
        association = managed(client)
        chloe = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", chloe)

        page = members_page(client, association["slug"])

        line = line_of(page, "Chloé")
        assert chloe in line
        assert "volunteer" in line.lower()
        assert "manager" in line_of(page, "Alice").lower()

    def test_lists_managers_first_then_by_display_name(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        add_member(client, association["id"], "Zoé", unique_email("Zoe"), "manager")
        add_member(client, association["id"], "Bruno", unique_email("Bruno"))

        page = members_page(client, association["slug"])

        names = [
            next(name for name in ("Alice", "Zoé", "Bruno", "Chloé") if name in line)
            for line in lines(page)
        ]
        assert names == ["Alice", "Zoé", "Bruno", "Chloé"]

    def test_shows_all_its_members_and_only_theirs(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))
        theirs = create_association(other, "Repair Café")
        add_member(other, theirs["id"], "David", unique_email("David"))

        page = members_page(client, association["slug"])

        assert len(lines(page)) == 2
        assert "Zoé" not in page
        assert "David" not in page

    def test_escapes_the_display_name(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "<b>Chloé</b>", unique_email("Chloe"))

        page = members_page(client, association["slug"])

        assert "<b>Chloé</b>" not in page
        assert "&lt;b&gt;Chloé&lt;/b&gt;" in page

    def test_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        client.cookies.set("language", "fr")

        page = members_page(client, association["slug"])

        assert "Membres" in part(page, "header")
        assert "responsable" in line_of(page, "Alice").lower()
        assert "bénévole" in line_of(page, "Chloé").lower()
        assert "pas encore connecté·e" in line_of(page, "Chloé")
        assert "Ajouter un membre" in text_of(part(page, "main"))

    def test_signed_out_shows_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)

        response = new_client().get(f"/association/{association['slug']}/members")

        assert response.status_code == 200
        assert 'type="password"' in response.text
        assert NAME not in response.text


class TestMembersHeader:
    def test_shows_the_association_name_then_members(self, client: Any) -> None:
        association = managed(client)

        header = text_of(part(members_page(client, association["slug"]), "header"))

        assert NAME in header
        assert header.index("Members") > header.index(NAME)
        assert "Alice" in header

    def test_the_association_name_leads_to_its_schedule(self, client: Any) -> None:
        association = managed(client)

        header = html.unescape(part(members_page(client, association["slug"]), "header"))

        assert re.search(
            rf'<a[^>]*href="/association/{association["slug"]}"[^>]*>\s*{NAME}\s*</a>', header
        )

    def test_the_location_stands_for_the_title(self, client: Any) -> None:
        association = managed(client)

        main = text_of(part(members_page(client, association["slug"]), "main"))

        assert "Members" not in main
        assert NAME not in main

    def test_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        client.cookies.set("language", "fr")

        header = text_of(part(members_page(client, association["slug"]), "header"))

        assert "Membres" in header


class TestNotJoinedYet:
    def test_shows_on_a_member_added_who_has_no_account(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))

        page = members_page(client, association["slug"])

        assert NOT_JOINED in line_of(page, "Chloé")
        assert NOT_JOINED not in line_of(page, "Alice")

    def test_shows_on_a_member_whose_account_is_not_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Bruno")
        add_member(client, association["id"], "Bruno", email)
        assert create_account(new_client(), "Bruno", email).status_code == 200

        assert NOT_JOINED in line_of(members_page(client, association["slug"]), "Bruno")

    def test_leaves_once_the_member_confirms_their_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Bruno")
        add_member(client, association["id"], "Bruno", email)
        bruno = new_client()
        create_account(bruno, "Bruno", email)
        confirm_email(bruno, latest_verification_token(email))

        assert NOT_JOINED not in line_of(members_page(client, association["slug"]), "Bruno")

    def test_leaves_once_the_member_signs_in_by_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", email)
        chloe = new_client()
        ask_for_link(chloe, email)
        open_link(chloe, latest_access_token(email))

        assert NOT_JOINED not in line_of(members_page(client, association["slug"]), "Chloé")


class TestShowAll:
    @pytest.mark.parametrize(("count", "shows_the_link"), [(5, False), (6, True), (7, True)])
    def test_shows_beyond_5_members(self, client: Any, count: int, shows_the_link: bool) -> None:
        association = managed(client)
        for n in range(count - 1):
            add_member(client, association["id"], f"Member {n}", unique_email(f"member{n}"))

        main = text_of(part(members_page(client, association["slug"]), "main"))

        assert (f"Show all {count} members" in main) is shows_the_link
        assert ("Show all" in main) is shows_the_link

    def test_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        for n in range(6):
            add_member(client, association["id"], f"Member {n}", unique_email(f"member{n}"))
        client.cookies.set("language", "fr")

        assert "Voir les 7 membres" in members_page(client, association["slug"])


class TestAsAManager:
    def test_shows_add_a_member(self, client: Any) -> None:
        association = managed(client)

        main = part(members_page(client, association["slug"]), "main")

        assert re.search(r"<button[^>]*>\s*\+\s*Add a member\s*</button>", main)

    def test_the_add_a_member_dialog_has_its_title_fields_and_buttons(self, client: Any) -> None:
        association = managed(client)

        main = part(members_page(client, association["slug"]), "main")

        dialog = re.search(r"<dialog.*?</dialog>", main, re.DOTALL)
        assert dialog, main
        form = dialog.group(0)
        assert re.search(r"<h2[^>]*>\s*Add a member\s*</h2>", form)
        assert re.search(r'<button[^>]*aria-label="Close"', form)
        assert re.search(r"<label[^>]*>\s*Display name\b", form)
        assert re.search(r"<label[^>]*>\s*Email\b", form)
        assert re.search(r"<label[^>]*>\s*Role\b", form)
        assert re.search(r'<option[^>]*value="volunteer"[^>]*selected', form)
        assert re.search(r'<option[^>]*value="manager"', form)
        assert re.search(r"<button[^>]*>\s*Add member\s*</button>", form)
        assert re.search(r"<button[^>]*>\s*Cancel\s*</button>", form)

    def test_each_member_has_its_edit_icon(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r'<button[^>]*aria-label="Edit Chloé"', main)
        assert re.search(r'<button[^>]*aria-label="Edit Alice"', main)

    def test_the_edit_icon_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        client.cookies.set("language", "fr")

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert 'aria-label="Modifier Chloé"' in main


class TestRebuildInProgress:
    def test_a_manager_sees_no_association_actions(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))

        page = members_page(client, association["slug"])

        assert "Rename the association" not in page
        assert "Change the association identifier" not in page
        assert "Delete the association" not in page

    def test_the_edit_dialog_has_no_sign_in_link_section(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))

        page = html.unescape(members_page(client, association["slug"]))

        assert "Remove from the association" in page
        assert "Sign-in link" not in page
        assert "SIGN-IN LINK" not in page
        assert "Send link" not in page
        assert "Revoke link" not in page


class TestAsAVolunteer:
    def test_shows_the_members_and_their_roles_without_add_a_member(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = members_page(bruno, association["slug"])

        assert "manager" in line_of(page, "Alice").lower()
        assert "volunteer" in line_of(page, "Bruno").lower()
        assert "Add a member" not in page
        assert "Add member" not in page
        assert "Edit Alice" not in page

    def test_shows_no_edit_dialog(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = html.unescape(members_page(bruno, association["slug"]))

        assert "Edit Bruno" not in page
        assert "Remove from the association" not in page
        assert "Remove Alice from the association?" not in page


class TestUnknownAssociation:
    def test_an_unknown_slug_says_so_with_a_way_to_my_associations(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get(f"/association/{unique_slug()}/members")

        main = html.unescape(part(response.text, "main"))
        assert UNKNOWN in main
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*My associations\s*</a>', main)
        assert "Page not found" not in response.text

    def test_an_association_of_others_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = other.get(f"/association/{association['slug']}/members")

        assert UNKNOWN in html.unescape(response.text)
        assert NAME not in response.text
        assert "Chloé" not in response.text

    def test_does_not_show_for_an_association_of_the_user(self, client: Any) -> None:
        association = managed(client)

        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))

    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = html.unescape(client.get(f"/association/{unique_slug()}/members").text)

        assert "Cette association n'existe pas ou vous n'en êtes pas membre." in page


class TestAddingAMember:
    def test_shows_the_member_added_and_says_so(self, client: Any) -> None:
        association = managed(client)
        email = unique_email("Chloe")

        text = shown(add_on_screen(client, association["slug"], "Chloé", email))

        assert "Chloé added." in text
        assert email in text
        page = members_page(client, association["slug"])
        assert email in line_of(page, "Chloé")
        assert "volunteer" in line_of(page, "Chloé").lower()

    def test_can_add_a_manager(self, client: Any) -> None:
        association = managed(client)

        shown(add_on_screen(client, association["slug"], "Zoé", unique_email("Zoe"), "manager"))

        assert "manager" in line_of(members_page(client, association["slug"]), "Zoé").lower()

    def test_otherwise_a_new_user_without_a_password_is_created(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        shown(add_on_screen(client, association["slug"], "Chloé", email))

        response = create_account(new_client(), "Chloé", email)

        assert response.status_code == 200
        assert email in shown(response)
        assert "An account already exists" not in shown(response)

    def test_r3_an_existing_user_keeps_their_display_name(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Bruno")
        sign_up(new_client(), "Bruno", email)

        text = shown(add_on_screen(client, association["slug"], "Someone else", email.upper()))

        assert "Bruno added." in text
        page = members_page(client, association["slug"])
        assert email in line_of(page, "Bruno")
        assert NOT_JOINED not in line_of(page, "Bruno")
        assert "Someone else" not in page

    def test_r3_a_user_added_to_two_associations_is_one_user(self, client: Any) -> None:
        sign_up(client, "Alice")
        first = create_association(client, NAME)
        second = create_association(client, "Repair Café Belleville")
        email = unique_email("Chloe")
        shown(add_on_screen(client, first["slug"], "Chloé", email))

        shown(add_on_screen(client, second["slug"], "Chloé B.", email))

        page = members_page(client, second["slug"])
        assert email in line_of(page, "Chloé")
        assert "Chloé B." not in page

    def test_an_existing_member_says_so_and_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", email)

        text = shown(add_on_screen(client, association["slug"], "Chloé", email, "manager"))

        assert "Chloé is already a member." in text
        assert "added." not in text
        assert member_count(client, association) == 2
        assert "volunteer" in line_of(members_page(client, association["slug"]), "Chloé").lower()

    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        client.cookies.set("language", "fr")

        slug = association["slug"]

        assert "Chloé ajouté·e." in shown(add_on_screen(client, slug, "Chloé", email))
        assert "Chloé est déjà membre." in shown(add_on_screen(client, slug, "Chloé", email))

    @pytest.mark.parametrize(
        "body",
        [
            {"email": "missing-name@example.org", "role": "volunteer"},
            {"displayName": "", "email": "empty-name@example.org", "role": "volunteer"},
            {"displayName": "Chloé", "role": "volunteer"},
            {"displayName": "Chloé", "email": "not-an-email", "role": "volunteer"},
            {"displayName": "Chloé", "email": "bad-role@example.org", "role": "president"},
            {"displayName": "Chloé", "email": "no-role@example.org"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_adds_no_one(
        self, client: Any, body: dict[str, str]
    ) -> None:
        association = managed(client)

        text = shown(client.post(f"/association/{association['slug']}/members", json=body))

        assert GENERIC in text
        assert "added." not in text
        assert member_count(client, association) == 1

    def test_a_volunteer_adds_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        response = add_on_screen(bruno, association["slug"], "Chloé", unique_email("Chloe"))

        assert "Chloé added." not in html.unescape(response.text)
        assert member_count(client, association) == 2

    def test_a_non_member_adds_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = add_on_screen(other, association["slug"], "Chloé", unique_email("Chloe"))

        assert "Chloé added." not in html.unescape(response.text)
        assert member_count(client, association) == 1

    def test_signed_out_leads_to_sign_in_and_adds_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)

        text = shown(add_on_screen(new_client(), association["slug"], "Chloé", unique_email("C")))

        assert "window.location" in text
        assert "added." not in text
        assert member_count(client, association) == 1


class TestChangingTheRole:
    def test_another_role_changes_it_and_says_so(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(client, association["slug"], chloe, "manager"))

        assert "Chloé is now manager." in text
        assert "manager" in role_of(client, association, "Chloé")

    def test_the_list_shows_the_new_role_at_once(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(client, association["slug"], chloe, "manager"))

        listed = [line for line in map(text_of, re.findall(r"<li.*?</li>", text, re.DOTALL))]
        assert any("Chloé" in line and "manager" in line.lower() for line in listed), text

    def test_a_manager_becomes_volunteer_when_another_manager_remains(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Zoé", unique_email("Zoe"), "manager")
        zoe = user_id(client, association, "Zoé")

        text = shown(change_role(client, association["slug"], zoe, "volunteer"))

        assert "Zoé is now volunteer." in text
        assert "volunteer" in role_of(client, association, "Zoé")

    def test_a_manager_may_demote_themself_when_another_manager_remains(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Zoé", unique_email("Zoe"), "manager")
        alice = user_id(client, association, "Alice")

        text = shown(change_role(client, association["slug"], alice, "volunteer"))

        assert "Alice is now volunteer." in text
        assert "Add a member" not in members_page(client, association["slug"])

    def test_the_member_promoted_can_manage_the_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        shown(change_role(client, association["slug"], member, "manager"))

        assert "Add a member" in members_page(bruno, association["slug"])

    def test_the_same_role_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(client, association["slug"], chloe, "volunteer"))

        assert "is now" not in text
        assert GENERIC not in text
        assert "volunteer" in role_of(client, association, "Chloé")

    def test_demoting_the_last_manager_says_so_and_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        alice = user_id(client, association, "Alice")

        text = shown(change_role(client, association["slug"], alice, "volunteer"))

        assert LAST_MANAGER in text
        assert "is now" not in text
        assert "manager" in role_of(client, association, "Alice")

    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")
        alice = user_id(client, association, "Alice")
        client.cookies.set("language", "fr")
        slug = association["slug"]

        promoted = shown(change_role(client, slug, chloe, "manager"))
        assert "Chloé est maintenant responsable." in promoted
        shown(change_role(client, slug, chloe, "volunteer"))
        assert "Une association garde au moins un responsable." in shown(
            change_role(client, slug, alice, "volunteer")
        )

    @pytest.mark.parametrize("body", [{}, {"role": ""}, {"role": "president"}])
    def test_a_missing_or_invalid_role_shows_the_generic_error_and_changes_nothing(
        self, client: Any, body: dict[str, str]
    ) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        path = f"/association/{association['slug']}/members/{chloe}/role"
        text = shown(client.post(path, json=body))

        assert GENERIC in text
        assert "volunteer" in role_of(client, association, "Chloé")

    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        zoe = sign_up(new_client(), "Zoé", unique_email("Zoe"))

        text = shown(change_role(client, association["slug"], zoe["id"], "manager"))

        assert GENERIC in text
        assert "Zoé" not in members_page(client, association["slug"])

    def test_a_volunteer_changes_no_role(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        response = change_role(bruno, association["slug"], member, "manager")

        assert "is now" not in html.unescape(response.text)
        assert "volunteer" in role_of(client, association, "Bruno")

    def test_a_non_member_changes_no_role(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        member = user_id(client, association, "Chloé")
        response = change_role(other, association["slug"], member, "manager")

        assert "is now" not in html.unescape(response.text)
        assert "volunteer" in role_of(client, association, "Chloé")

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(new_client(), association["slug"], chloe, "manager"))

        assert "window.location" in text
        assert "is now" not in text
        assert "volunteer" in role_of(client, association, "Chloé")


class TestRemovingAMember:
    def test_removes_the_member_and_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        text = shown(remove_member(client, association["slug"], member))

        assert "Bruno is removed." in text
        assert "Bruno" not in text_of(part(members_page(client, association["slug"]), "main"))
        page = bruno.get(f"/association/{association['slug']}/members")
        assert UNKNOWN in html.unescape(page.text)
        assert association["name"] not in bruno.get("/").text

    def test_the_list_leaves_out_the_member_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, _ = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        text = shown(remove_member(client, association["slug"], member))

        listed = [text_of(item) for item in re.findall(r"<li.*?</li>", text, re.DOTALL)]
        assert any("Alice" in line for line in listed), text
        assert not any("Bruno" in line for line in listed)

    def test_the_user_can_be_added_again(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        members = client.get(f"/api/associations/{association['id']}").json()["members"]
        email = next(m["email"] for m in members if m["display_name"] == "Bruno")
        shown(remove_member(client, association["slug"], user_id(client, association, "Bruno")))

        text = shown(add_on_screen(client, association["slug"], "Bruno", email))

        assert "Bruno added." in text
        assert UNKNOWN not in html.unescape(members_page(bruno, association["slug"]))

    def test_a_manager_removes_another_manager(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Zoé", unique_email("Zoe"), "manager")

        member = user_id(client, association, "Zoé")
        text = shown(remove_member(client, association["slug"], member))

        assert "Zoé is removed." in text
        assert "Zoé" not in members_page(client, association["slug"])

    def test_removing_the_last_manager_says_so_and_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))

        member = user_id(client, association, "Alice")
        text = shown(remove_member(client, association["slug"], member))

        assert LAST_MANAGER in text
        assert "is removed." not in text
        assert "manager" in role_of(client, association, "Alice")

    def test_a_manager_who_removes_themself_is_led_to_my_associations(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Zoé", unique_email("Zoe"), "manager")

        member = user_id(client, association, "Alice")
        text = shown(remove_member(client, association["slug"], member))

        assert re.search(r"window\.location = '/'", text), text
        page = html.unescape(client.get(f"/association/{association['slug']}/members").text)
        assert UNKNOWN in page

    def test_the_confirmation_asks_with_the_member_name(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))

        page = html.unescape(members_page(client, association["slug"]))

        assert (
            "Remove Chloé from the association? Their upcoming registrations are cancelled." in page
        )

    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        alice = user_id(client, association, "Alice")
        chloe = user_id(client, association, "Chloé")
        client.cookies.set("language", "fr")
        slug = association["slug"]

        assert "Une association garde au moins un responsable." in shown(
            remove_member(client, slug, alice)
        )
        assert "Chloé est retiré·e." in shown(remove_member(client, slug, chloe))

    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        zoe = sign_up(new_client(), "Zoé", unique_email("Zoe"))

        text = shown(remove_member(client, association["slug"], zoe["id"]))

        assert GENERIC in text
        assert "is removed." not in text

    def test_a_volunteer_removes_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        response = remove_member(bruno, association["slug"], user_id(client, association, "Bruno"))

        assert "is removed." not in html.unescape(response.text)
        assert member_count(client, association) == 2

    def test_a_non_member_removes_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = remove_member(other, association["slug"], user_id(client, association, "Chloé"))

        assert "is removed." not in html.unescape(response.text)
        assert member_count(client, association) == 2

    def test_signed_out_leads_to_sign_in_and_removes_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["id"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(remove_member(new_client(), association["slug"], chloe))

        assert "window.location" in text
        assert "is removed." not in text
        assert member_count(client, association) == 2
