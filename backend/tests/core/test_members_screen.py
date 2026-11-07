import html
import re
import time
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    ask_for_link,
    break_the_mailer,
    change_identifier,
    change_role,
    confirm_email,
    create_account,
    create_association,
    delete_association,
    email_count,
    latest_access_token,
    latest_email,
    latest_verification_token,
    names_listed,
    open_link,
    remove_member,
    rename_association,
    revoke_member_link,
    send_member_link,
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
REVOKE_CHLOE = "Revoke Chloé's sign-in link?"
LINK_SUBJECT = {"en": "Your sign-in link", "fr": "Votre lien de connexion"}
NEW_NAME = "Jardin des Lilas"
MALFORMED_SLUG = (
    "Use only lowercase letters, digits and hyphens, starting and ending with a letter or a digit."
)
TAKEN_SLUG = "This association identifier is already taken."
CONFIRM_DELETE = (
    f"Delete {NAME}? Its schedule and its members' registrations are erased. This cannot be undone."
)


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


def signs_in(client: Any, token: str) -> bool:
    """Runs the action of Access link, and tells whether it leads on, signed in."""
    return "window.location" in shown(open_link(client, token))


def no_email_sent(email: str, already: int = 0) -> bool:
    """Waits for a stray email to arrive, then tells whether `email` got only `already`."""
    time.sleep(0.5)
    return email_count(email) == already


def with_link(client: Any, new_client: Callable[[], Any]) -> tuple[dict[str, Any], str, str]:
    """Alice manages an association where Chloé, added by her, asked for her access link."""
    association = managed(client)
    email = unique_email("Chloe")
    add_member(client, association["id"], "Chloé", email)
    ask_for_link(new_client(), email)
    return association, user_id(client, association, "Chloé"), latest_access_token(email)


def with_member(client: Any) -> tuple[dict[str, Any], str, str]:
    """Alice manages an association where she added Chloé, who has no access link."""
    association = managed(client)
    email = unique_email("Chloe")
    add_member(client, association["id"], "Chloé", email)
    return association, user_id(client, association, "Chloé"), email


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

        main = part(members_page(client, association["slug"]), "main")
        shown_in_main = text_of(re.sub(r"<dialog.*?</dialog>", "", main, flags=re.DOTALL))

        assert "Members" not in shown_in_main
        assert NAME not in shown_in_main

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

    def test_shows_no_association_actions(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = html.unescape(members_page(bruno, association["slug"]))

        assert "Rename the association" not in page
        assert "Change the association identifier" not in page
        assert "Delete the association" not in page
        assert f"Delete {NAME}?" not in page


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


class TestSignInLinkSection:
    def test_the_edit_dialog_offers_send_link_with_its_confirmation(self, client: Any) -> None:
        association, _, _ = with_member(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r">\s*Sign-in link\s*<", main, re.IGNORECASE)
        assert re.search(r"<button[^>]*>\s*Send link\s*</button>", main)
        assert "Send Chloé's sign-in link by email?" in main
        assert re.search(r"<button[^>]*>\s*Send\s*</button>", main)

    def test_revoke_link_shows_only_for_a_member_with_an_access_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, _, email = with_member(client)
        slug = association["slug"]
        assert REVOKE_CHLOE not in html.unescape(members_page(client, slug))

        ask_for_link(new_client(), email)

        main = html.unescape(part(members_page(client, slug), "main"))
        assert REVOKE_CHLOE in main
        assert re.search(r"<button[^>]*>\s*Revoke link\s*</button>", main)
        assert re.search(r"<button[^>]*>\s*Revoke\s*</button>", main)

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _, _ = with_link(client, new_client)
        client.cookies.set("language", "fr")

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r">\s*Lien de connexion\s*<", main, re.IGNORECASE)
        assert "Envoyer le lien de connexion de Chloé par e-mail ?" in main
        assert "Révoquer le lien de connexion de Chloé ?" in main

    def test_a_volunteer_sees_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = html.unescape(members_page(bruno, association["slug"]))

        assert "Send link" not in page
        assert "Revoke link" not in page
        assert "Send Alice's sign-in link by email?" not in page


class TestRevokingALink:
    def test_r23_revokes_the_link_and_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, token = with_link(client, new_client)
        phone = new_client()
        open_link(phone, token)

        text = shown(revoke_member_link(client, association["slug"], chloe))

        assert "Chloé's sign-in link is revoked." in text
        assert phone.get("/api/session").status_code == 401
        assert not signs_in(new_client(), token)
        assert REVOKE_CHLOE not in html.unescape(members_page(client, association["slug"]))

    def test_the_dialog_no_longer_offers_revoke_link_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, _ = with_link(client, new_client)

        text = shown(revoke_member_link(client, association["slug"], chloe))

        assert "Chloé" in text
        assert REVOKE_CHLOE not in text

    def test_r23_keeps_the_members_password_sessions_signed_in(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)
        email = next(
            m["email"]
            for m in client.get(f"/api/associations/{association['id']}").json()["members"]
            if m["display_name"] == "Bruno"
        )
        ask_for_link(new_client(), email)
        token = latest_access_token(email)

        member = user_id(client, association, "Bruno")
        shown(revoke_member_link(client, association["slug"], member))

        assert bruno.get("/api/session").status_code == 200
        assert not signs_in(new_client(), token)

    def test_the_message_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, _ = with_link(client, new_client)
        client.cookies.set("language", "fr")

        text = shown(revoke_member_link(client, association["slug"], chloe))

        assert "Le lien de connexion de Chloé est révoqué." in text

    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Zoe")
        zoe = sign_up(new_client(), "Zoé", email)
        ask_for_link(new_client(), email)
        token = latest_access_token(email)

        text = shown(revoke_member_link(client, association["slug"], zoe["id"]))

        assert GENERIC in text
        assert "is revoked." not in text
        assert signs_in(new_client(), token)

    def test_a_volunteer_revokes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, token = with_link(client, new_client)
        bruno = new_client()
        bruno_email = unique_email("Bruno")
        sign_up(bruno, "Bruno", bruno_email)
        add_member(client, association["id"], "Bruno", bruno_email)

        response = revoke_member_link(bruno, association["slug"], chloe)

        assert "is revoked." not in html.unescape(response.text)
        assert signs_in(new_client(), token)

    def test_a_non_member_revokes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, token = with_link(client, new_client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = revoke_member_link(other, association["slug"], chloe)

        assert "is revoked." not in html.unescape(response.text)
        assert signs_in(new_client(), token)

    def test_signed_out_leads_to_sign_in_and_revokes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, token = with_link(client, new_client)

        text = shown(revoke_member_link(new_client(), association["slug"], chloe))

        assert "window.location" in text
        assert "is revoked." not in text
        assert signs_in(new_client(), token)


class TestSendingALink:
    def test_r26_sends_the_email_and_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, email = with_member(client)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert "Chloé's sign-in link is sent." in text
        assert latest_email(email)["Subject"] == LINK_SUBJECT["en"]
        browser = new_client()
        assert signs_in(browser, latest_access_token(email))
        assert browser.get("/api/session").json()["id"] == chloe

    def test_the_dialog_offers_revoke_link_at_once(self, client: Any) -> None:
        association, chloe, _ = with_member(client)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert REVOKE_CHLOE in text

    def test_r26_the_email_and_the_message_follow_the_managers_language(self, client: Any) -> None:
        association, chloe, email = with_member(client)

        response = send_member_link(
            client,
            association["slug"],
            chloe,
            headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
        )

        assert "Le lien de connexion de Chloé est envoyé." in shown(response)
        assert latest_email(email)["Subject"] == LINK_SUBJECT["fr"]

    def test_r20_r26_the_managers_language_cookie_wins_over_their_browser(
        self, client: Any
    ) -> None:
        association, chloe, email = with_member(client)
        client.cookies.set("language", "fr")

        send_member_link(client, association["slug"], chloe, headers={"Accept-Language": "en"})

        assert latest_email(email)["Subject"] == LINK_SUBJECT["fr"]

    def test_r26_r25_sending_again_sends_the_same_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, first_token = with_link(client, new_client)
        email = next(
            m["email"]
            for m in client.get(f"/api/associations/{association['id']}").json()["members"]
            if m["display_name"] == "Chloé"
        )
        time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

        shown(send_member_link(client, association["slug"], chloe))

        assert email_count(email) == 2
        assert latest_access_token(email) == first_token

    def test_r26_a_manager_sends_their_own_link(self, client: Any) -> None:
        association, _, _ = with_member(client)
        alice = next(
            m
            for m in client.get(f"/api/associations/{association['id']}").json()["members"]
            if m["display_name"] == "Alice"
        )

        text = shown(send_member_link(client, association["slug"], alice["user_id"]))

        assert "Alice's sign-in link is sent." in text
        latest_access_token(alice["email"])

    def test_when_the_email_cannot_be_sent_says_so(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        association, chloe, email = with_member(client)
        break_the_mailer(monkeypatch)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert "We couldn't send Chloé's sign-in link. Try again later." in text
        assert "is sent." not in text
        monkeypatch.undo()
        assert no_email_sent(email)

    def test_when_the_email_cannot_be_sent_follows_the_language(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        association, chloe, _ = with_member(client)
        client.cookies.set("language", "fr")
        break_the_mailer(monkeypatch)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert "Le lien de connexion de Chloé n'a pas pu être envoyé. Réessayez plus tard." in text

    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Zoe")
        zoe = sign_up(new_client(), "Zoé", email)
        time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

        text = shown(send_member_link(client, association["slug"], zoe["id"]))

        assert GENERIC in text
        assert "is sent." not in text
        assert no_email_sent(email, already=1)  # only the confirmation email

    def test_a_volunteer_sends_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["id"], "Chloé", chloe_email)

        response = send_member_link(
            bruno, association["slug"], user_id(client, association, "Chloé")
        )

        assert "is sent." not in html.unescape(response.text)
        assert no_email_sent(chloe_email)

    def test_a_non_member_sends_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, email = with_member(client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = send_member_link(other, association["slug"], chloe)

        assert "is sent." not in html.unescape(response.text)
        assert no_email_sent(email)

    def test_signed_out_leads_to_sign_in_and_sends_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, email = with_member(client)

        text = shown(send_member_link(new_client(), association["slug"], chloe))

        assert "window.location" in text
        assert "is sent." not in text
        assert no_email_sent(email)


class TestLinkEndpointsRemoved:
    @pytest.mark.parametrize("method", ["POST", "DELETE"])
    def test_answer_404(self, client: Any, method: str) -> None:
        association, chloe, _ = with_member(client)

        path = f"/api/associations/{association['id']}/members/{chloe}/access-link"

        assert client.request(method, path).status_code == 404


def name_of(client: Any, association: dict[str, Any]) -> str:
    found: str = client.get(f"/api/associations/{association['id']}").json()["name"]
    return found


def slug_of(client: Any, association: dict[str, Any]) -> str:
    found: str = client.get(f"/api/associations/{association['id']}").json()["slug"]
    return found


def email_of(client: Any, association: dict[str, Any], display_name: str) -> str:
    members = client.get(f"/api/associations/{association['id']}").json()["members"]
    found: str = next(m["email"] for m in members if m["display_name"] == display_name)
    return found


def promoted(client: Any, association: dict[str, Any], display_name: str) -> None:
    """Alice makes `display_name` a manager."""
    member = user_id(client, association, display_name)
    assert "is now manager." in shown(change_role(client, association["slug"], member, "manager"))


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


class TestAssociationActions:
    def test_a_manager_sees_the_three_actions(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r"<button[^>]*>\s*Rename the association\s*</button>", main)
        assert re.search(r"<button[^>]*>\s*Change the association identifier\s*</button>", main)
        assert re.search(r"<button[^>]*>\s*Delete the association\s*</button>", main)

    def test_rename_the_association_opens_its_dialog(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r"<h2[^>]*>\s*Rename the association\s*</h2>", main)
        assert re.search(r"<label[^>]*>\s*Name\b", main)

    def test_change_the_association_identifier_opens_its_dialog(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r"<h2[^>]*>\s*Change the association identifier\s*</h2>", main)
        assert re.search(r"<label[^>]*>\s*Association identifier\b", main)
        assert "/association/" in text_of(main)

    def test_delete_the_association_asks_with_its_name(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert CONFIRM_DELETE in main
        assert "Type the association's name to confirm" in main
        assert re.search(r"<button[^>]*>\s*Delete\s*</button>", main)

    def test_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        client.cookies.set("language", "fr")

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert "Renommer l'association" in main
        assert "Modifier l'identifiant de l'association" in main
        assert "Supprimer l'association" in main
        assert f"Supprimer {NAME} ? Son planning" in main
        assert "Saisissez le nom de l'association pour confirmer" in main


class TestRenamingTheAssociation:
    def test_another_name_changes_it_and_says_so(self, client: Any) -> None:
        association = managed(client)

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        assert f"The association is now {NEW_NAME}." in text
        assert name_of(client, association) == NEW_NAME
        assert NEW_NAME in text_of(part(members_page(client, association["slug"]), "header"))
        assert NEW_NAME in client.get("/").text

    def test_updates_the_header_at_once(self, client: Any) -> None:
        association = managed(client)

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        slug = association["slug"]
        assert re.search(rf'<a[^>]*href="/association/{slug}"[^>]*>\s*{NEW_NAME}\s*</a>', text)

    def test_the_slug_stays_unchanged(self, client: Any) -> None:
        association = managed(client)

        shown(rename_association(client, association["slug"], NEW_NAME))

        assert slug_of(client, association) == association["slug"]
        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))

    def test_the_same_name_changes_nothing(self, client: Any) -> None:
        association = managed(client)

        text = shown(rename_association(client, association["slug"], NAME))

        assert "is now" not in text
        assert GENERIC not in text
        assert name_of(client, association) == NAME

    def test_accepts_the_name_of_another_association(self, client: Any) -> None:
        association = managed(client)
        create_association(client, NEW_NAME)

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        assert f"The association is now {NEW_NAME}." in text
        assert name_of(client, association) == NEW_NAME

    def test_escapes_the_name(self, client: Any) -> None:
        association = managed(client)

        response = rename_association(client, association["slug"], "<b>Jardin</b>")

        assert "<b>Jardin</b>" not in response.text
        assert "<b>Jardin</b>" not in members_page(client, association["slug"])

    def test_by_any_manager(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")

        shown(rename_association(bruno, association["slug"], NEW_NAME))

        assert name_of(client, association) == NEW_NAME

    def test_the_members_are_not_told(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _ = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        before = email_count(email)

        shown(rename_association(client, association["slug"], NEW_NAME))

        assert no_email_sent(email, already=before)

    def test_the_message_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        client.cookies.set("language", "fr")

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        assert f"L'association s'appelle désormais {NEW_NAME}." in text

    @pytest.mark.parametrize("body", [{}, {"name": ""}])
    def test_a_missing_or_empty_name_shows_the_generic_error_and_changes_nothing(
        self, client: Any, body: dict[str, str]
    ) -> None:
        association = managed(client)

        text = shown(client.post(f"/association/{association['slug']}/rename", json=body))

        assert GENERIC in text
        assert name_of(client, association) == NAME

    def test_a_volunteer_renames_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        response = rename_association(bruno, association["slug"], NEW_NAME)

        assert "is now" not in html.unescape(response.text)
        assert name_of(client, association) == NAME

    def test_a_non_member_renames_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)

        response = rename_association(other_user(new_client), association["slug"], NEW_NAME)

        assert "is now" not in html.unescape(response.text)
        assert name_of(client, association) == NAME

    def test_signed_out_leads_to_sign_in_and_renames_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)

        text = shown(rename_association(new_client(), association["slug"], NEW_NAME))

        assert "window.location" in text
        assert "is now" not in text
        assert name_of(client, association) == NAME


class TestChangingTheIdentifier:
    def test_another_slug_changes_it_and_leads_to_its_new_url(self, client: Any) -> None:
        association = managed(client)
        slug = unique_slug()

        text = shown(change_identifier(client, association["slug"], slug))

        assert re.search(rf"window\.location = '/association/{slug}/members'", text), text
        assert slug_of(client, association) == slug
        assert NAME in members_page(client, slug)

    def test_accepts_a_slug_of_50_characters(self, client: Any) -> None:
        association = managed(client)
        slug = unique_slug().ljust(50, "x")

        shown(change_identifier(client, association["slug"], slug))

        assert slug_of(client, association) == slug

    def test_r36_the_former_slug_no_longer_leads_to_the_association(self, client: Any) -> None:
        association = managed(client)

        shown(change_identifier(client, association["slug"], unique_slug()))

        page = html.unescape(client.get(f"/association/{association['slug']}/members").text)
        assert UNKNOWN in page

    def test_r36_another_association_can_take_the_former_slug(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        shown(change_identifier(client, association["slug"], unique_slug()))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        theirs = create_association(other, "Repair Café", association["slug"])

        assert "Repair Café" in members_page(other, theirs["slug"])

    def test_the_same_slug_changes_nothing(self, client: Any) -> None:
        association = managed(client)

        text = shown(change_identifier(client, association["slug"], association["slug"]))

        assert "is now" not in text
        assert GENERIC not in text
        assert TAKEN_SLUG not in text
        assert slug_of(client, association) == association["slug"]

    @pytest.mark.parametrize(
        "slug", ["Jardin", "jardin lilas", "jardin_lilas", "-jardin", "jardin-", "jardín", "a" * 51]
    )
    def test_a_malformed_slug_shows_its_message(self, client: Any, slug: str) -> None:
        association = managed(client)

        text = shown(change_identifier(client, association["slug"], slug))

        assert MALFORMED_SLUG in text
        assert "window.location" not in text
        assert slug_of(client, association) == association["slug"]

    def test_a_slug_taken_by_another_association_shows_its_message(self, client: Any) -> None:
        association = managed(client)
        other = create_association(client, "Repair Café", unique_slug())

        text = shown(change_identifier(client, association["slug"], other["slug"]))

        assert TAKEN_SLUG in text
        assert slug_of(client, association) == association["slug"]

    def test_the_slug_new_shows_the_taken_message(self, client: Any) -> None:
        association = managed(client)

        text = shown(change_identifier(client, association["slug"], "new"))

        assert TAKEN_SLUG in text
        assert slug_of(client, association) == association["slug"]

    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        other = create_association(client, "Repair Café", unique_slug())
        client.cookies.set("language", "fr")
        slug = association["slug"]

        assert "Utilisez uniquement des lettres minuscules" in shown(
            change_identifier(client, slug, "Jardin")
        )
        assert "Cet identifiant d'association est déjà pris." in shown(
            change_identifier(client, slug, other["slug"])
        )

    def test_a_missing_slug_shows_the_generic_error(self, client: Any) -> None:
        association = managed(client)

        text = shown(client.post(f"/association/{association['slug']}/identifier", json={}))

        assert GENERIC in text
        assert slug_of(client, association) == association["slug"]

    def test_by_any_manager(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")
        slug = unique_slug()

        shown(change_identifier(bruno, association["slug"], slug))

        assert slug_of(client, association) == slug

    def test_the_members_are_not_told(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _ = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        before = email_count(email)

        shown(change_identifier(client, association["slug"], unique_slug()))

        assert no_email_sent(email, already=before)

    def test_a_volunteer_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        slug = unique_slug()

        response = change_identifier(bruno, association["slug"], slug)

        assert slug not in response.text
        assert slug_of(client, association) == association["slug"]

    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        slug = unique_slug()

        response = change_identifier(other_user(new_client), association["slug"], slug)

        assert slug not in response.text
        assert slug_of(client, association) == association["slug"]

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        slug = unique_slug()

        text = shown(change_identifier(new_client(), association["slug"], slug))

        assert "window.location" in text
        assert slug not in text
        assert slug_of(client, association) == association["slug"]


class TestDeletingTheAssociation:
    def test_deletes_it_and_leads_to_my_associations(self, client: Any) -> None:
        association = managed(client)

        text = shown(delete_association(client, association["slug"]))

        assert re.search(r"window\.location = '/'", text), text
        assert client.get(f"/api/associations/{association['id']}").status_code == 404
        assert names_listed(client) == []
        page = html.unescape(client.get(f"/association/{association['slug']}/members").text)
        assert UNKNOWN in page

    def test_by_any_manager(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")

        shown(delete_association(bruno, association["slug"]))

        assert names_listed(client) == []

    def test_r34_members_stay_users_in_their_other_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        add_member(client, other["id"], "Bruno", email_of(client, association, "Bruno"))

        shown(delete_association(client, association["slug"]))

        assert bruno.get("/api/session").status_code == 200
        assert names_listed(bruno) == [other["name"]]
        assert "Repair Café Belleville" in members_page(client, other["slug"])

    def test_r34_a_member_left_in_no_association_stays_a_user(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)

        shown(delete_association(client, association["slug"]))

        assert bruno.get("/api/session").status_code == 200
        assert names_listed(bruno) == []

    def test_r34_an_added_user_can_be_added_to_another_association_afterwards(
        self, client: Any
    ) -> None:
        association, chloe, email = with_member(client)
        shown(delete_association(client, association["slug"]))
        other = create_association(client, "Repair Café Belleville", unique_slug())

        text = shown(add_on_screen(client, other["slug"], "Chloé", email))

        assert "Chloé added." in text
        assert user_id(client, other, "Chloé") == chloe

    def test_r34_the_members_are_not_told(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _ = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        before = email_count(email)

        shown(delete_association(client, association["slug"]))

        assert no_email_sent(email, already=before)

    def test_a_volunteer_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        delete_association(bruno, association["slug"])

        assert client.get(f"/api/associations/{association['id']}").status_code == 200

    def test_a_non_member_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)

        delete_association(other_user(new_client), association["slug"])

        assert client.get(f"/api/associations/{association['id']}").status_code == 200

    def test_signed_out_leads_to_sign_in_and_deletes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)

        text = shown(delete_association(new_client(), association["slug"]))

        assert "window.location" in text
        assert client.get(f"/api/associations/{association['id']}").status_code == 200


class TestAssociationEndpointsRemoved:
    @pytest.mark.parametrize(("method", "body"), [("PATCH", {"name": NEW_NAME}), ("DELETE", None)])
    def test_patch_and_delete_api_association_change_nothing(
        self, client: Any, method: str, body: dict[str, str] | None
    ) -> None:
        association = managed(client)

        response = client.request(method, f"/api/associations/{association['id']}", json=body)

        assert response.status_code in (404, 405)
        assert name_of(client, association) == NAME
