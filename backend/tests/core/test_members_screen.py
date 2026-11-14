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
    members_roles,
    names_listed,
    open_link,
    remove_member,
    rename_association,
    revoke_member_link,
    run_sql,
    run_sql_rows,
    send_member_link,
    shown,
    sign_up,
    signed_in_as,
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
    """The number of members that Members lists."""
    return len(members_roles(client, association["slug"]))


def _of_member(column: str, association: dict[str, Any], display_name: str) -> str:
    found = run_sql_rows(
        f"SELECT u.{column} FROM user_account u JOIN membership m ON m.user_id = u.id"
        " WHERE m.association_id = :association AND u.display_name = :name",
        association=association["id"],
        name=display_name,
    )
    assert len(found) == 1, found
    return str(found[0][0])


def user_id(client: Any, association: dict[str, Any], display_name: str) -> str:
    """The user ID of the member `display_name`, read from the database: no screen shows it."""
    return _of_member("id", association, display_name)


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
    add_member(client, association["slug"], "Chloé", email)
    ask_for_link(new_client(), email)
    return association, user_id(client, association, "Chloé"), latest_access_token(email)


def with_member(client: Any) -> tuple[dict[str, Any], str, str]:
    """Alice manages an association where she added Chloé, who has no access link."""
    association = managed(client)
    email = unique_email("Chloe")
    add_member(client, association["slug"], "Chloé", email)
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
    add_member(client, association["slug"], "Bruno", email)
    return association, bruno


class TestMembers:
    # /core/ui/members/list
    def test_shows_each_member_with_email_and_role(self, client: Any) -> None:
        association = managed(client)
        chloe = unique_email("Chloe")
        add_member(client, association["slug"], "Chloé", chloe)

        page = members_page(client, association["slug"])

        line = line_of(page, "Chloé")
        assert chloe in line
        assert "volunteer" in line.lower()
        assert "manager" in line_of(page, "Alice").lower()

    # /core/ui/members/list
    def test_lists_managers_first_then_by_display_name(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        add_member(client, association["slug"], "Zoé", unique_email("Zoe"), "manager")
        add_member(client, association["slug"], "Bruno", unique_email("Bruno"))

        page = members_page(client, association["slug"])

        names = [
            next(name for name in ("Alice", "Zoé", "Bruno", "Chloé") if name in line)
            for line in lines(page)
        ]
        assert names == ["Alice", "Zoé", "Bruno", "Chloé"]

    # /core/ui/members/list
    def test_shows_all_its_members_and_only_theirs(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))
        theirs = create_association(other, "Repair Café")
        add_member(other, theirs["slug"], "David", unique_email("David"))

        page = members_page(client, association["slug"])

        assert len(lines(page)) == 2
        assert "Zoé" not in page
        assert "David" not in page

    # /core/ui/members/list
    def test_escapes_the_display_name(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "<b>Chloé</b>", unique_email("Chloe"))

        page = members_page(client, association["slug"])

        assert "<b>Chloé</b>" not in page
        assert "&lt;b&gt;Chloé&lt;/b&gt;" in page

    # /core/ui/members/list
    # /core/ui/members/not-joined
    # /core/ui/members/manager
    # /core/ui/header/location
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        client.cookies.set("language", "fr")

        page = members_page(client, association["slug"])

        assert "Membres" in part(page, "header")
        assert "responsable" in line_of(page, "Alice").lower()
        assert "bénévole" in line_of(page, "Chloé").lower()
        assert "pas encore connecté·e" in line_of(page, "Chloé")
        assert "Ajouter un membre" in text_of(part(page, "main"))

    # /core/ui/access/signed-out
    def test_signed_out_shows_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)

        response = new_client().get(f"/association/{association['slug']}/members")

        assert response.status_code == 200
        assert 'type="password"' in response.text
        assert NAME not in response.text


class TestMembersHeader:
    # /core/ui/header/location
    # /core/ui/header/menu
    def test_shows_the_association_name_then_members(self, client: Any) -> None:
        association = managed(client)

        header = text_of(part(members_page(client, association["slug"]), "header"))

        assert NAME in header
        assert header.index("Members") > header.index(NAME)
        assert "Alice" in header

    # /core/ui/header/association-link
    def test_the_association_name_leads_to_its_schedule(self, client: Any) -> None:
        association = managed(client)

        header = html.unescape(part(members_page(client, association["slug"]), "header"))

        assert re.search(
            rf'<a[^>]*href="/association/{association["slug"]}"[^>]*>\s*{NAME}\s*</a>', header
        )

    # /core/ui/header/title
    def test_the_location_stands_for_the_title(self, client: Any) -> None:
        association = managed(client)

        main = part(members_page(client, association["slug"]), "main")
        shown_in_main = text_of(re.sub(r"<dialog.*?</dialog>", "", main, flags=re.DOTALL))

        assert "Members" not in shown_in_main
        assert NAME not in shown_in_main

    # /core/ui/header/location
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        client.cookies.set("language", "fr")

        header = text_of(part(members_page(client, association["slug"]), "header"))

        assert "Membres" in header


class TestNotJoinedYet:
    # /core/ui/members/not-joined
    def test_shows_on_a_member_added_who_has_no_account(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))

        page = members_page(client, association["slug"])

        assert NOT_JOINED in line_of(page, "Chloé")
        assert NOT_JOINED not in line_of(page, "Alice")

    # /core/ui/members/not-joined
    def test_shows_on_a_member_whose_account_is_not_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Bruno")
        add_member(client, association["slug"], "Bruno", email)
        assert create_account(new_client(), "Bruno", email).status_code == 200

        assert NOT_JOINED in line_of(members_page(client, association["slug"]), "Bruno")

    # /core/ui/members/not-joined
    # /core/operations/confirm-email/confirmed
    def test_leaves_once_the_member_confirms_their_email(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Bruno")
        add_member(client, association["slug"], "Bruno", email)
        bruno = new_client()
        create_account(bruno, "Bruno", email)
        confirm_email(bruno, latest_verification_token(email))

        assert NOT_JOINED not in line_of(members_page(client, association["slug"]), "Bruno")

    # /core/ui/members/not-joined
    # /core/operations/sign-in-by-access-link/signed-in
    def test_leaves_once_the_member_signs_in_by_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        add_member(client, association["slug"], "Chloé", email)
        chloe = new_client()
        ask_for_link(chloe, email)
        open_link(chloe, latest_access_token(email))

        assert NOT_JOINED not in line_of(members_page(client, association["slug"]), "Chloé")


class TestShowAll:
    # /core/ui/members/first-five
    @pytest.mark.parametrize(("count", "shows_the_link"), [(5, False), (6, True), (7, True)])
    def test_shows_beyond_5_members(self, client: Any, count: int, shows_the_link: bool) -> None:
        association = managed(client)
        for n in range(count - 1):
            add_member(client, association["slug"], f"Member {n}", unique_email(f"member{n}"))

        main = text_of(part(members_page(client, association["slug"]), "main"))

        assert (f"Show all {count} members" in main) is shows_the_link
        assert ("Show all" in main) is shows_the_link

    # /core/ui/members/first-five
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        for n in range(6):
            add_member(client, association["slug"], f"Member {n}", unique_email(f"member{n}"))
        client.cookies.set("language", "fr")

        assert "Voir les 7 membres" in members_page(client, association["slug"])


class TestAsAManager:
    # /core/ui/members/manager
    # /ui/forms/create
    def test_shows_add_a_member(self, client: Any) -> None:
        association = managed(client)

        main = part(members_page(client, association["slug"]), "main")

        assert re.search(r"<button[^>]*>\s*\+\s*Add a member\s*</button>", main)

    # /core/ui/members/add
    # /ui/forms/dialog
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

    # /core/ui/members/manager
    # /ui/forms/icon-names
    def test_each_member_has_its_edit_icon(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r'<button[^>]*aria-label="Edit Chloé"', main)
        assert re.search(r'<button[^>]*aria-label="Edit Alice"', main)

    # /core/ui/members/manager
    # /core/ui/header/language
    def test_the_edit_icon_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        client.cookies.set("language", "fr")

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert 'aria-label="Modifier Chloé"' in main


class TestAsAVolunteer:
    # /core/ui/members/volunteer
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

    # /core/ui/members/volunteer
    def test_shows_no_edit_dialog(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = html.unescape(members_page(bruno, association["slug"]))

        assert "Edit Bruno" not in page
        assert "Remove from the association" not in page
        assert "Remove Alice from the association?" not in page

    # /core/ui/members/volunteer
    def test_shows_no_association_actions(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = html.unescape(members_page(bruno, association["slug"]))

        assert "Rename the association" not in page
        assert "Change the association identifier" not in page
        assert "Delete the association" not in page
        assert f"Delete {NAME}?" not in page


class TestUnknownAssociation:
    # /core/ui/unknown-association/shown
    def test_an_unknown_slug_says_so_with_a_way_to_my_associations(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get(f"/association/{unique_slug()}/members")

        main = html.unescape(part(response.text, "main"))
        assert UNKNOWN in main
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*My associations\s*</a>', main)
        assert "Page not found" not in response.text

    # /core/ui/unknown-association/shown
    def test_an_association_of_others_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = other.get(f"/association/{association['slug']}/members")

        assert UNKNOWN in html.unescape(response.text)
        assert NAME not in response.text
        assert "Chloé" not in response.text

    # /core/ui/unknown-association/status
    def test_answers_200_for_an_unknown_slug_and_an_association_of_others(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        for path in (
            f"/association/{unique_slug()}",
            f"/association/{association['slug']}",
            f"/association/{association['slug']}/members",
        ):
            response = other.get(path)
            assert response.status_code == 200, path
            assert UNKNOWN in html.unescape(response.text), path

    # /core/ui/unknown-association/shown
    def test_does_not_show_for_an_association_of_the_user(self, client: Any) -> None:
        association = managed(client)

        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))

    # /core/ui/unknown-association/shown
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = html.unescape(client.get(f"/association/{unique_slug()}/members").text)

        assert "Cette association n'existe pas ou vous n'en êtes pas membre." in page


class TestAddingAMember:
    # /core/ui/members/added
    # /core/operations/add-member/new-user
    def test_shows_the_member_added_and_says_so(self, client: Any) -> None:
        association = managed(client)
        email = unique_email("Chloe")

        text = shown(add_on_screen(client, association["slug"], "Chloé", email))

        assert "Chloé added." in text
        assert email in text
        page = members_page(client, association["slug"])
        assert email in line_of(page, "Chloé")
        assert "volunteer" in line_of(page, "Chloé").lower()

    # /core/operations/add-member/new-user
    def test_can_add_a_manager(self, client: Any) -> None:
        association = managed(client)

        shown(add_on_screen(client, association["slug"], "Zoé", unique_email("Zoe"), "manager"))

        assert "manager" in line_of(members_page(client, association["slug"]), "Zoé").lower()

    # /core/operations/add-member/new-user
    # /core/operations/create-account/claimed
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

    # /core/operations/add-member/existing-user
    # /core/ui/members/added
    # /core/model/user/email
    def test_an_existing_user_keeps_their_display_name(
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

    # /core/operations/add-member/existing-user
    def test_a_user_added_to_two_associations_is_one_user(self, client: Any) -> None:
        sign_up(client, "Alice")
        first = create_association(client, NAME)
        second = create_association(client, "Repair Café Belleville")
        email = unique_email("Chloe")
        shown(add_on_screen(client, first["slug"], "Chloé", email))

        shown(add_on_screen(client, second["slug"], "Chloé B.", email))

        page = members_page(client, second["slug"])
        assert email in line_of(page, "Chloé")
        assert "Chloé B." not in page

    # /core/ui/members/already
    # /core/operations/add-member/already
    # /core/model/membership/single
    def test_an_existing_member_says_so_and_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        add_member(client, association["slug"], "Chloé", email)

        text = shown(add_on_screen(client, association["slug"], "Chloé", email, "manager"))

        assert "Chloé is already a member." in text
        assert "added." not in text
        assert member_count(client, association) == 2
        assert "volunteer" in line_of(members_page(client, association["slug"]), "Chloé").lower()

    # /core/ui/members/added
    # /core/ui/members/already
    # /core/ui/header/language
    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        email = unique_email("Chloe")
        client.cookies.set("language", "fr")

        slug = association["slug"]

        assert "Chloé ajouté·e." in shown(add_on_screen(client, slug, "Chloé", email))
        assert "Chloé est déjà membre." in shown(add_on_screen(client, slug, "Chloé", email))

    # /ui/errors/generic
    # /core/operations/general/refused
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

    # /core/operations/general/manager
    def test_a_volunteer_adds_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        response = add_on_screen(bruno, association["slug"], "Chloé", unique_email("Chloe"))

        assert "Chloé added." not in html.unescape(response.text)
        assert member_count(client, association) == 2

    # /core/operations/general/unknown-association
    def test_a_non_member_adds_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = add_on_screen(other, association["slug"], "Chloé", unique_email("Chloe"))

        assert "Chloé added." not in html.unescape(response.text)
        assert member_count(client, association) == 1

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_adds_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)

        text = shown(add_on_screen(new_client(), association["slug"], "Chloé", unique_email("C")))

        assert "window.location" in text
        assert "added." not in text
        assert member_count(client, association) == 1


class TestChangingTheRole:
    # /core/ui/members/changed
    # /core/operations/change-role/changed
    # /core/ui/members/save
    def test_another_role_changes_it_and_says_so(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(client, association["slug"], chloe, "manager"))

        assert "Chloé is now manager." in text
        assert "manager" in role_of(client, association, "Chloé")

    # /core/ui/members/changed
    # /ui/forms/success
    def test_the_list_shows_the_new_role_at_once(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(client, association["slug"], chloe, "manager"))

        listed = [line for line in map(text_of, re.findall(r"<li.*?</li>", text, re.DOTALL))]
        assert any("Chloé" in line and "manager" in line.lower() for line in listed), text

    # /core/ui/members/changed
    # /core/operations/change-role/changed
    def test_a_manager_becomes_volunteer_when_another_manager_remains(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Zoé", unique_email("Zoe"), "manager")
        zoe = user_id(client, association, "Zoé")

        text = shown(change_role(client, association["slug"], zoe, "volunteer"))

        assert "Zoé is now volunteer." in text
        assert "volunteer" in role_of(client, association, "Zoé")

    # /core/ui/members/changed
    # /core/operations/change-role/changed
    # /core/ui/members/volunteer
    def test_a_manager_may_demote_themself_when_another_manager_remains(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Zoé", unique_email("Zoe"), "manager")
        alice = user_id(client, association, "Alice")

        text = shown(change_role(client, association["slug"], alice, "volunteer"))

        assert "Alice is now volunteer." in text
        assert "Add a member" not in members_page(client, association["slug"])

    # /core/operations/change-role/changed
    # /core/ui/members/manager
    def test_the_member_promoted_can_manage_the_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        shown(change_role(client, association["slug"], member, "manager"))

        assert "Add a member" in members_page(bruno, association["slug"])

    # /core/ui/members/same-role
    def test_the_same_role_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(client, association["slug"], chloe, "volunteer"))

        assert "is now" not in text
        assert GENERIC not in text
        assert "volunteer" in role_of(client, association, "Chloé")

    # /core/ui/members/last-manager
    # /core/operations/change-role/last-manager
    # /core/model/membership/manager
    def test_demoting_the_last_manager_says_so_and_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        alice = user_id(client, association, "Alice")

        text = shown(change_role(client, association["slug"], alice, "volunteer"))

        assert LAST_MANAGER in text
        assert "is now" not in text
        assert "manager" in role_of(client, association, "Alice")

    # /core/ui/members/changed
    # /core/ui/members/last-manager
    # /core/ui/header/language
    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
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

    # /ui/errors/generic
    # /core/operations/general/refused
    @pytest.mark.parametrize("body", [{}, {"role": ""}, {"role": "president"}])
    def test_a_missing_or_invalid_role_shows_the_generic_error_and_changes_nothing(
        self, client: Any, body: dict[str, str]
    ) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        path = f"/association/{association['slug']}/members/{chloe}/role"
        text = shown(client.post(path, json=body))

        assert GENERIC in text
        assert "volunteer" in role_of(client, association, "Chloé")

    # /ui/errors/generic
    # /core/operations/change-role/not-member
    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        zoe = sign_up(new_client(), "Zoé", unique_email("Zoe"))

        text = shown(change_role(client, association["slug"], zoe["id"], "manager"))

        assert GENERIC in text
        assert "Zoé" not in members_page(client, association["slug"])

    # /core/operations/general/manager
    def test_a_volunteer_changes_no_role(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        response = change_role(bruno, association["slug"], member, "manager")

        assert "is now" not in html.unescape(response.text)
        assert "volunteer" in role_of(client, association, "Bruno")

    # /core/operations/general/unknown-association
    def test_a_non_member_changes_no_role(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        member = user_id(client, association, "Chloé")
        response = change_role(other, association["slug"], member, "manager")

        assert "is now" not in html.unescape(response.text)
        assert "volunteer" in role_of(client, association, "Chloé")

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(change_role(new_client(), association["slug"], chloe, "manager"))

        assert "window.location" in text
        assert "is now" not in text
        assert "volunteer" in role_of(client, association, "Chloé")


class TestRemovingAMember:
    # /core/ui/members/removed
    # /core/operations/remove-member/removed
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

    # /core/ui/members/removed
    # /ui/forms/success
    def test_the_list_leaves_out_the_member_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, _ = with_volunteer(client, new_client)

        member = user_id(client, association, "Bruno")
        text = shown(remove_member(client, association["slug"], member))

        listed = [text_of(item) for item in re.findall(r"<li.*?</li>", text, re.DOTALL)]
        assert any("Alice" in line for line in listed), text
        assert not any("Bruno" in line for line in listed)

    # /core/operations/remove-member/removed
    # /core/operations/add-member/existing-user
    def test_the_user_can_be_added_again(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        shown(remove_member(client, association["slug"], user_id(client, association, "Bruno")))

        text = shown(add_on_screen(client, association["slug"], "Bruno", email))

        assert "Bruno added." in text
        assert UNKNOWN not in html.unescape(members_page(bruno, association["slug"]))

    # /core/ui/members/removed
    # /core/operations/remove-member/removed
    def test_a_manager_removes_another_manager(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Zoé", unique_email("Zoe"), "manager")

        member = user_id(client, association, "Zoé")
        text = shown(remove_member(client, association["slug"], member))

        assert "Zoé is removed." in text
        assert "Zoé" not in members_page(client, association["slug"])

    # /core/ui/members/remove-last-manager
    # /core/operations/remove-member/last-manager
    # /core/model/membership/manager
    def test_removing_the_last_manager_says_so_and_changes_nothing(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))

        member = user_id(client, association, "Alice")
        text = shown(remove_member(client, association["slug"], member))

        assert LAST_MANAGER in text
        assert "is removed." not in text
        assert "manager" in role_of(client, association, "Alice")

    # /core/ui/members/remove-last-manager
    # /core/operations/remove-member/last-manager
    def test_the_only_member_cannot_remove_themself(self, client: Any) -> None:
        association = managed(client)

        member = user_id(client, association, "Alice")
        text = shown(remove_member(client, association["slug"], member))

        assert LAST_MANAGER in text
        assert "window.location" not in text
        assert "manager" in role_of(client, association, "Alice")

    # /core/ui/members/themself
    # /core/operations/remove-member/removed
    def test_a_manager_who_removes_themself_is_led_to_my_associations(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Zoé", unique_email("Zoe"), "manager")

        member = user_id(client, association, "Alice")
        text = shown(remove_member(client, association["slug"], member))

        assert re.search(r"window\.location = '/'", text), text
        page = html.unescape(client.get(f"/association/{association['slug']}/members").text)
        assert UNKNOWN in page

    # /core/ui/members/remove
    def test_the_confirmation_asks_with_the_member_name(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))

        page = html.unescape(members_page(client, association["slug"]))

        assert (
            "Remove Chloé from the association? Their upcoming registrations are cancelled." in page
        )

    # /core/ui/members/removed
    # /core/ui/members/remove-last-manager
    # /core/ui/header/language
    def test_messages_follow_the_language(self, client: Any) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        alice = user_id(client, association, "Alice")
        chloe = user_id(client, association, "Chloé")
        client.cookies.set("language", "fr")
        slug = association["slug"]

        assert "Une association garde au moins un responsable." in shown(
            remove_member(client, slug, alice)
        )
        assert "Chloé est retiré·e." in shown(remove_member(client, slug, chloe))

    # /ui/errors/generic
    # /core/operations/remove-member/not-member
    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        zoe = sign_up(new_client(), "Zoé", unique_email("Zoe"))

        text = shown(remove_member(client, association["slug"], zoe["id"]))

        assert GENERIC in text
        assert "is removed." not in text

    # /core/operations/general/manager
    def test_a_volunteer_removes_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        response = remove_member(bruno, association["slug"], user_id(client, association, "Bruno"))

        assert "is removed." not in html.unescape(response.text)
        assert member_count(client, association) == 2

    # /core/operations/general/unknown-association
    def test_a_non_member_removes_no_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = remove_member(other, association["slug"], user_id(client, association, "Chloé"))

        assert "is removed." not in html.unescape(response.text)
        assert member_count(client, association) == 2

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_removes_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        add_member(client, association["slug"], "Chloé", unique_email("Chloe"))
        chloe = user_id(client, association, "Chloé")

        text = shown(remove_member(new_client(), association["slug"], chloe))

        assert "window.location" in text
        assert "is removed." not in text
        assert member_count(client, association) == 2


class TestSignInLinkSection:
    # /core/ui/members/edit
    # /core/ui/members/send-link
    def test_the_edit_dialog_offers_send_link_with_its_confirmation(self, client: Any) -> None:
        association, _, _ = with_member(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r">\s*Sign-in link\s*<", main, re.IGNORECASE)
        assert re.search(r"<button[^>]*>\s*Send link\s*</button>", main)
        assert "Send Chloé's sign-in link by email?" in main
        assert re.search(r"<button[^>]*>\s*Send\s*</button>", main)

    # /core/ui/members/revoke-link
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

    # /core/ui/members/edit
    # /core/ui/members/send-link
    # /core/ui/members/revoke-link
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _, _ = with_link(client, new_client)
        client.cookies.set("language", "fr")

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r">\s*Lien de connexion\s*<", main, re.IGNORECASE)
        assert "Envoyer le lien de connexion de Chloé par e-mail ?" in main
        assert "Révoquer le lien de connexion de Chloé ?" in main

    # /core/ui/members/volunteer
    def test_a_volunteer_sees_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        page = html.unescape(members_page(bruno, association["slug"]))

        assert "Send link" not in page
        assert "Revoke link" not in page
        assert "Send Alice's sign-in link by email?" not in page


class TestRevokingALink:
    # /core/ui/members/revoke-link
    # /core/operations/revoke-access-link/revoked
    def test_revokes_the_link_and_says_so(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, token = with_link(client, new_client)
        phone = new_client()
        open_link(phone, token)

        text = shown(revoke_member_link(client, association["slug"], chloe))

        assert "Chloé's sign-in link is revoked." in text
        assert signed_in_as(phone) is None
        assert not signs_in(new_client(), token)
        assert REVOKE_CHLOE not in html.unescape(members_page(client, association["slug"]))

    # /core/ui/members/revoke-link
    # /ui/forms/success
    def test_the_dialog_no_longer_offers_revoke_link_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, _ = with_link(client, new_client)

        text = shown(revoke_member_link(client, association["slug"], chloe))

        assert "Chloé" in text
        assert REVOKE_CHLOE not in text

    # /core/operations/revoke-access-link/revoked
    def test_keeps_the_members_password_sessions_signed_in(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        ask_for_link(new_client(), email)
        token = latest_access_token(email)

        member = user_id(client, association, "Bruno")
        shown(revoke_member_link(client, association["slug"], member))

        assert signed_in_as(bruno) is not None
        assert not signs_in(new_client(), token)

    # /core/ui/members/revoke-link
    # /core/ui/header/language
    def test_the_message_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, _ = with_link(client, new_client)
        client.cookies.set("language", "fr")

        text = shown(revoke_member_link(client, association["slug"], chloe))

        assert "Le lien de connexion de Chloé est révoqué." in text

    # /ui/errors/generic
    # /core/operations/revoke-access-link/not-member
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

    # /core/operations/general/manager
    def test_a_volunteer_revokes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, token = with_link(client, new_client)
        bruno = new_client()
        bruno_email = unique_email("Bruno")
        sign_up(bruno, "Bruno", bruno_email)
        add_member(client, association["slug"], "Bruno", bruno_email)

        response = revoke_member_link(bruno, association["slug"], chloe)

        assert "is revoked." not in html.unescape(response.text)
        assert signs_in(new_client(), token)

    # /core/operations/general/unknown-association
    def test_a_non_member_revokes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, token = with_link(client, new_client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = revoke_member_link(other, association["slug"], chloe)

        assert "is revoked." not in html.unescape(response.text)
        assert signs_in(new_client(), token)

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_revokes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, token = with_link(client, new_client)

        text = shown(revoke_member_link(new_client(), association["slug"], chloe))

        assert "window.location" in text
        assert "is revoked." not in text
        assert signs_in(new_client(), token)


class TestSendingALink:
    # /core/ui/members/sent
    # /core/operations/send-access-link/sent
    def test_sends_the_email_and_says_so(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, email = with_member(client)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert "Chloé's sign-in link is sent." in text
        assert latest_email(email)["Subject"] == LINK_SUBJECT["en"]
        browser = new_client()
        assert signs_in(browser, latest_access_token(email))
        assert signed_in_as(browser) == "Chloé"

    # /core/ui/members/revoke-link
    # /ui/forms/success
    def test_the_dialog_offers_revoke_link_at_once(self, client: Any) -> None:
        association, chloe, _ = with_member(client)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert REVOKE_CHLOE in text

    # /core/ui/members/sent
    # /core/operations/send-access-link/sent
    # /ui/language/default
    # /ui/language/emails
    def test_the_email_and_the_message_follow_the_managers_language(self, client: Any) -> None:
        association, chloe, email = with_member(client)

        response = send_member_link(
            client,
            association["slug"],
            chloe,
            headers={"Accept-Language": "fr-FR,fr;q=0.9,en;q=0.8"},
        )

        assert "Le lien de connexion de Chloé est envoyé." in shown(response)
        assert latest_email(email)["Subject"] == LINK_SUBJECT["fr"]

    # /core/operations/send-access-link/sent
    # /core/ui/header/language
    def test_the_managers_language_cookie_wins_over_their_browser(self, client: Any) -> None:
        association, chloe, email = with_member(client)
        client.cookies.set("language", "fr")

        send_member_link(client, association["slug"], chloe, headers={"Accept-Language": "en"})

        assert latest_email(email)["Subject"] == LINK_SUBJECT["fr"]

    # /core/operations/send-access-link/sent
    # /core/operations/request-access-link/same
    def test_sending_again_sends_the_same_link(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, first_token = with_link(client, new_client)
        email = email_of(client, association, "Chloé")
        time.sleep(0.01)  # Mailpit orders by Created, at millisecond precision.

        shown(send_member_link(client, association["slug"], chloe))

        assert email_count(email) == 2
        assert latest_access_token(email) == first_token

    # /core/ui/members/sent
    # /core/operations/send-access-link/sent
    def test_a_manager_sends_their_own_link(self, client: Any) -> None:
        association, _, _ = with_member(client)
        alice = user_id(client, association, "Alice")

        text = shown(send_member_link(client, association["slug"], alice))

        assert "Alice's sign-in link is sent." in text
        latest_access_token(email_of(client, association, "Alice"))

    # /core/ui/members/not-sent
    # /core/operations/send-access-link/not-sent
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

    # /core/ui/members/not-sent
    # /core/ui/header/language
    def test_when_the_email_cannot_be_sent_follows_the_language(
        self, client: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        association, chloe, _ = with_member(client)
        client.cookies.set("language", "fr")
        break_the_mailer(monkeypatch)

        text = shown(send_member_link(client, association["slug"], chloe))

        assert "Le lien de connexion de Chloé n'a pas pu être envoyé. Réessayez plus tard." in text

    # /ui/errors/generic
    # /core/operations/send-access-link/not-member
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

    # /core/operations/general/manager
    def test_a_volunteer_sends_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        chloe_email = unique_email("Chloe")
        add_member(client, association["slug"], "Chloé", chloe_email)

        response = send_member_link(
            bruno, association["slug"], user_id(client, association, "Chloé")
        )

        assert "is sent." not in html.unescape(response.text)
        assert no_email_sent(chloe_email)

    # /core/operations/general/unknown-association
    def test_a_non_member_sends_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, chloe, email = with_member(client)
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        response = send_member_link(other, association["slug"], chloe)

        assert "is sent." not in html.unescape(response.text)
        assert no_email_sent(email)

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_sends_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, chloe, email = with_member(client)

        text = shown(send_member_link(new_client(), association["slug"], chloe))

        assert "window.location" in text
        assert "is sent." not in text
        assert no_email_sent(email)


def name_of(client: Any, association: dict[str, Any]) -> str:
    """The association's name, read from the database by its id, which no change alters."""
    return str(run_sql("SELECT name FROM association WHERE id = :id", id=association["id"]))


def slug_of(client: Any, association: dict[str, Any]) -> str:
    """The association's slug, read from the database by its id, which no change alters."""
    return str(run_sql("SELECT slug FROM association WHERE id = :id", id=association["id"]))


def email_of(client: Any, association: dict[str, Any], display_name: str) -> str:
    """The email of the member `display_name`, read from the database."""
    return _of_member("email", association, display_name)


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
    # /core/ui/members/manager
    def test_a_manager_sees_the_three_actions(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r"<button[^>]*>\s*Rename the association\s*</button>", main)
        assert re.search(r"<button[^>]*>\s*Change the association identifier\s*</button>", main)
        assert re.search(r"<button[^>]*>\s*Delete the association\s*</button>", main)

    # /core/ui/members/rename
    def test_rename_the_association_opens_its_dialog(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r"<h2[^>]*>\s*Rename the association\s*</h2>", main)
        assert re.search(r"<label[^>]*>\s*Name\b", main)

    # /core/ui/members/change-slug
    def test_change_the_association_identifier_opens_its_dialog(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert re.search(r"<h2[^>]*>\s*Change the association identifier\s*</h2>", main)
        assert re.search(r"<label[^>]*>\s*Association identifier\b", main)
        assert "/association/" in text_of(main)

    # /core/ui/members/delete
    def test_delete_the_association_asks_with_its_name(self, client: Any) -> None:
        association = managed(client)

        main = html.unescape(part(members_page(client, association["slug"]), "main"))

        assert CONFIRM_DELETE in main
        assert "Type the association's name to confirm" in main
        assert re.search(r"<button[^>]*>\s*Delete\s*</button>", main)

    # /core/ui/members/manager
    # /core/ui/members/delete
    # /core/ui/header/language
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
    # /core/ui/members/renamed
    # /core/operations/update-association/renamed
    # /core/operations/update-association/changed
    def test_another_name_changes_it_and_says_so(self, client: Any) -> None:
        association = managed(client)

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        assert f"The association is now {NEW_NAME}." in text
        assert name_of(client, association) == NEW_NAME
        assert NEW_NAME in text_of(part(members_page(client, association["slug"]), "header"))
        assert NEW_NAME in client.get("/").text

    # /core/ui/members/renamed
    # /core/ui/header/association-link
    def test_updates_the_header_at_once(self, client: Any) -> None:
        association = managed(client)

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        slug = association["slug"]
        assert re.search(rf'<a[^>]*href="/association/{slug}"[^>]*>\s*{NEW_NAME}\s*</a>', text)

    # /core/operations/update-association/renamed
    def test_the_slug_stays_unchanged(self, client: Any) -> None:
        association = managed(client)

        shown(rename_association(client, association["slug"], NEW_NAME))

        assert slug_of(client, association) == association["slug"]
        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))

    # /core/ui/members/same-name
    def test_the_same_name_changes_nothing(self, client: Any) -> None:
        association = managed(client)

        text = shown(rename_association(client, association["slug"], NAME))

        assert "is now" not in text
        assert GENERIC not in text
        assert name_of(client, association) == NAME

    # /core/ui/members/renamed
    # /core/operations/update-association/renamed
    def test_accepts_the_name_of_another_association(self, client: Any) -> None:
        association = managed(client)
        create_association(client, NEW_NAME)

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        assert f"The association is now {NEW_NAME}." in text
        assert name_of(client, association) == NEW_NAME

    # /core/ui/members/renamed
    def test_escapes_the_name(self, client: Any) -> None:
        association = managed(client)

        response = rename_association(client, association["slug"], "<b>Jardin</b>")

        assert "<b>Jardin</b>" not in response.text
        assert "<b>Jardin</b>" not in members_page(client, association["slug"])

    # /core/operations/update-association/renamed
    def test_by_any_manager(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")

        shown(rename_association(bruno, association["slug"], NEW_NAME))

        assert name_of(client, association) == NEW_NAME

    # /core/operations/update-association/silent
    def test_the_members_are_not_told(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _ = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        before = email_count(email)

        shown(rename_association(client, association["slug"], NEW_NAME))

        assert no_email_sent(email, already=before)

    # /core/ui/members/renamed
    # /core/ui/header/language
    def test_the_message_follows_the_language(self, client: Any) -> None:
        association = managed(client)
        client.cookies.set("language", "fr")

        text = shown(rename_association(client, association["slug"], NEW_NAME))

        assert f"L'association s'appelle désormais {NEW_NAME}." in text

    # /ui/errors/generic
    # /core/model/association/name
    @pytest.mark.parametrize("body", [{}, {"name": ""}])
    def test_a_missing_or_empty_name_shows_the_generic_error_and_changes_nothing(
        self, client: Any, body: dict[str, str]
    ) -> None:
        association = managed(client)

        text = shown(client.post(f"/association/{association['slug']}/rename", json=body))

        assert GENERIC in text
        assert name_of(client, association) == NAME

    # /core/operations/general/manager
    def test_a_volunteer_renames_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        response = rename_association(bruno, association["slug"], NEW_NAME)

        assert "is now" not in html.unescape(response.text)
        assert name_of(client, association) == NAME

    # /core/operations/general/unknown-association
    def test_a_non_member_renames_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)

        response = rename_association(other_user(new_client), association["slug"], NEW_NAME)

        assert "is now" not in html.unescape(response.text)
        assert name_of(client, association) == NAME

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_renames_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)

        text = shown(rename_association(new_client(), association["slug"], NEW_NAME))

        assert "window.location" in text
        assert "is now" not in text
        assert name_of(client, association) == NAME


class TestChangingTheIdentifier:
    # /core/ui/members/slug-changed
    # /core/operations/update-association/new-slug
    def test_another_slug_changes_it_and_leads_to_its_new_url(self, client: Any) -> None:
        association = managed(client)
        slug = unique_slug()

        text = shown(change_identifier(client, association["slug"], slug))

        assert re.search(rf"window\.location = '/association/{slug}/members'", text), text
        assert slug_of(client, association) == slug
        assert NAME in members_page(client, slug)

    # /core/model/association/slug-format
    # /core/operations/update-association/new-slug
    def test_accepts_a_slug_of_50_characters(self, client: Any) -> None:
        association = managed(client)
        slug = unique_slug().ljust(50, "x")

        shown(change_identifier(client, association["slug"], slug))

        assert slug_of(client, association) == slug

    # /core/operations/update-association/new-slug
    # /core/ui/unknown-association/shown
    def test_the_former_slug_no_longer_leads_to_the_association(self, client: Any) -> None:
        association = managed(client)

        shown(change_identifier(client, association["slug"], unique_slug()))

        page = html.unescape(client.get(f"/association/{association['slug']}/members").text)
        assert UNKNOWN in page

    # /core/operations/update-association/new-slug
    def test_another_association_can_take_the_former_slug(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)
        shown(change_identifier(client, association["slug"], unique_slug()))
        other = new_client()
        sign_up(other, "Zoé", unique_email("Zoe"))

        theirs = create_association(other, "Repair Café", association["slug"])

        assert "Repair Café" in members_page(other, theirs["slug"])

    # /core/ui/members/same-slug
    def test_the_same_slug_changes_nothing(self, client: Any) -> None:
        association = managed(client)

        text = shown(change_identifier(client, association["slug"], association["slug"]))

        assert "is now" not in text
        assert GENERIC not in text
        assert TAKEN_SLUG not in text
        assert slug_of(client, association) == association["slug"]

    # /core/ui/members/refused
    # /core/operations/update-association/malformed-slug
    # /core/model/association/slug-format
    @pytest.mark.parametrize(
        "slug", ["Jardin", "jardin lilas", "jardin_lilas", "-jardin", "jardin-", "jardín", "a" * 51]
    )
    def test_a_malformed_slug_shows_its_message(self, client: Any, slug: str) -> None:
        association = managed(client)

        text = shown(change_identifier(client, association["slug"], slug))

        assert MALFORMED_SLUG in text
        assert "window.location" not in text
        assert slug_of(client, association) == association["slug"]

    # /core/ui/members/refused
    # /core/operations/update-association/taken
    def test_a_slug_taken_by_another_association_shows_its_message(self, client: Any) -> None:
        association = managed(client)
        other = create_association(client, "Repair Café", unique_slug())

        text = shown(change_identifier(client, association["slug"], other["slug"]))

        assert TAKEN_SLUG in text
        assert slug_of(client, association) == association["slug"]

    # /core/ui/members/refused
    # /core/operations/update-association/taken
    def test_the_slug_new_shows_the_taken_message(self, client: Any) -> None:
        association = managed(client)

        text = shown(change_identifier(client, association["slug"], "new"))

        assert TAKEN_SLUG in text
        assert slug_of(client, association) == association["slug"]

    # /core/ui/members/refused
    # /core/ui/header/language
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

    # /ui/errors/generic
    # /core/operations/general/refused
    def test_a_missing_slug_shows_the_generic_error(self, client: Any) -> None:
        association = managed(client)

        text = shown(client.post(f"/association/{association['slug']}/identifier", json={}))

        assert GENERIC in text
        assert slug_of(client, association) == association["slug"]

    # /core/operations/update-association/new-slug
    def test_by_any_manager(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")
        slug = unique_slug()

        shown(change_identifier(bruno, association["slug"], slug))

        assert slug_of(client, association) == slug

    # /core/operations/update-association/silent
    def test_the_members_are_not_told(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _ = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        before = email_count(email)

        shown(change_identifier(client, association["slug"], unique_slug()))

        assert no_email_sent(email, already=before)

    # /core/operations/general/manager
    def test_a_volunteer_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        slug = unique_slug()

        response = change_identifier(bruno, association["slug"], slug)

        assert "is now" not in html.unescape(response.text)
        assert slug_of(client, association) == association["slug"]

    # /core/operations/general/unknown-association
    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)
        slug = unique_slug()

        response = change_identifier(other_user(new_client), association["slug"], slug)

        assert slug not in response.text
        assert slug_of(client, association) == association["slug"]

    # /core/ui/access/action
    # /core/operations/general/signed-out
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
    # /core/ui/members/delete
    # /core/operations/delete-association/deleted
    def test_deletes_it_and_leads_to_my_associations(self, client: Any) -> None:
        association = managed(client)

        text = shown(delete_association(client, association["slug"]))

        assert re.search(r"window\.location = '/'", text), text
        assert names_listed(client) == []
        page = html.unescape(client.get(f"/association/{association['slug']}/members").text)
        assert UNKNOWN in page

    # /core/operations/delete-association/deleted
    def test_by_any_manager(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")

        shown(delete_association(bruno, association["slug"]))

        assert names_listed(client) == []

    # /core/operations/delete-association/silent
    def test_members_stay_users_in_their_other_associations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        add_member(client, other["slug"], "Bruno", email_of(client, association, "Bruno"))

        shown(delete_association(client, association["slug"]))

        assert signed_in_as(bruno) is not None
        assert names_listed(bruno) == [other["name"]]
        assert "Repair Café Belleville" in members_page(client, other["slug"])

    # /core/operations/delete-association/silent
    def test_a_member_left_in_no_association_stays_a_user(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)

        shown(delete_association(client, association["slug"]))

        assert signed_in_as(bruno) is not None
        assert names_listed(bruno) == []

    # /core/operations/delete-association/silent
    # /core/operations/add-member/existing-user
    def test_an_added_user_can_be_added_to_another_association_afterwards(
        self, client: Any
    ) -> None:
        association, chloe, email = with_member(client)
        shown(delete_association(client, association["slug"]))
        other = create_association(client, "Repair Café Belleville", unique_slug())

        text = shown(add_on_screen(client, other["slug"], "Chloé", email))

        assert "Chloé added." in text
        assert user_id(client, other, "Chloé") == chloe

    # /core/operations/delete-association/silent
    def test_the_members_are_not_told(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, _ = with_volunteer(client, new_client)
        email = email_of(client, association, "Bruno")
        before = email_count(email)

        shown(delete_association(client, association["slug"]))

        assert no_email_sent(email, already=before)

    # /core/ui/members/delete-refused
    # /core/operations/general/manager
    def test_refused_shows_members_again_as_it_now_is(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")
        assert "Delete the association" in html.unescape(members_page(bruno, association["slug"]))
        member = user_id(client, association, "Bruno")
        shown(change_role(client, association["slug"], member, "volunteer"))

        text = shown(delete_association(bruno, association["slug"]))

        assert f"window.location = '/association/{association['slug']}/members'" in text, text
        page = html.unescape(members_page(bruno, association["slug"]))
        assert UNKNOWN not in page
        assert "Delete the association" not in page

    # /core/ui/members/delete-refused
    # /core/operations/general/unknown-association
    def test_refused_once_deleted_shows_the_unknown_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association, bruno = with_volunteer(client, new_client)
        promoted(client, association, "Bruno")
        shown(delete_association(client, association["slug"]))

        text = shown(delete_association(bruno, association["slug"]))

        assert f"window.location = '/association/{association['slug']}/members'" in text, text
        assert UNKNOWN in html.unescape(members_page(bruno, association["slug"]))

    # /core/operations/general/manager
    def test_a_volunteer_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association, bruno = with_volunteer(client, new_client)

        delete_association(bruno, association["slug"])

        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))

    # /core/operations/general/unknown-association
    def test_a_non_member_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        association = managed(client)

        delete_association(other_user(new_client), association["slug"])

        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))

    # /core/ui/access/action
    # /core/operations/general/signed-out
    def test_signed_out_leads_to_sign_in_and_deletes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        association = managed(client)

        text = shown(delete_association(new_client(), association["slug"]))

        assert "window.location" in text
        assert UNKNOWN not in html.unescape(members_page(client, association["slug"]))
