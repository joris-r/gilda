# ruff: noqa: RUF001  (times and dates are written with an en dash, as the screen shows them)
import html
import re
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from tests.core.conftest import delete_association, unique_slug
from tests.planning.conftest import (
    GENERIC,
    MONTHS,
    Planning,
    add_absence,
    add_absence_on_screen,
    availability_lines,
    availability_page,
    availability_section,
    create_association,
    delete_absence,
    edit_absence,
    lines_of,
    notes_offered,
    part,
    preferences_stored,
    save_note,
    section_of,
    set_my_preference,
    shown,
    sign_up,
    text_of,
    unique_email,
    without_dialogs,
    write_note,
)

NAME = "Jardin partagé des Lilas"
UNKNOWN = "This association does not exist or you are not a member."
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
THU = "Thu 10:00–13:00"


def collapsed(fragment: str) -> str:
    return " ".join(text_of(fragment).split())


def selected(select: str) -> str:
    """The label of the option a selector shows chosen, or of its first one when none is."""
    options = re.findall(r"<option([^>]*)>(.*?)</option>", select, re.DOTALL)
    assert options, select
    chosen = [label for attributes, label in options if re.search(r"\bselected\b", attributes)]
    assert len(chosen) <= 1, select
    return collapsed(chosen[0] if chosen else options[0][1])


def preferences_shown(
    client: Any, slug: str, heading: str = "My preferences"
) -> list[tuple[str, str]]:
    """Each line of My preferences: its slot, and the value its selector shows."""
    section = section_of(availability_page(client, slug), heading)
    lines = []
    for item in re.findall(r"<li.*?</li>", section, re.DOTALL):
        selects = re.findall(r"<select.*?</select>", item, re.DOTALL)
        assert len(selects) == 1, item
        slot = collapsed(re.sub(r"<select.*?</select>", "", item, flags=re.DOTALL))
        lines.append((slot, selected(selects[0])))
    return lines


def selector_labels(client: Any, slug: str, heading: str = "My preferences") -> list[str]:
    """The labels of the options of the first selector of My preferences, in order."""
    section = section_of(availability_page(client, slug), heading)
    select = re.search(r"<select.*?</select>", section, re.DOTALL)
    assert select, section
    return [collapsed(label) for label in re.findall(r"<option[^>]*>(.*?)</option>", select[0])]


def chosen(planning: Planning, as_client: Any, slot: dict[str, Any], value: str) -> None:
    text = shown(set_my_preference(as_client, planning.slug, slot["id"], value))
    assert GENERIC not in text, text


def stored(planning: Planning) -> set[tuple[str, str, str]]:
    """The preferences of the association, as Alice's Members' preferences shows them."""
    return preferences_stored(planning.alice_client, planning.slug)


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


class TestMyPreferences:
    def test_lists_each_slot_with_its_selector(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")

        assert preferences_shown(planning.bruno_client, planning.slug) == [
            ("Thursday 10:00–13:00", "—"),
            ("Saturday 10:00–13:00", "—"),
        ]

    def test_slots_are_listed_by_weekday_then_start(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        planning.add_slot("thursday", "13:00", "16:00")
        planning.add_slot("monday", "18:30", "20:15")
        planning.add_slot("thursday", "10:00", "13:00")

        assert [slot for slot, _ in preferences_shown(planning.bruno_client, planning.slug)] == [
            "Monday 18:30–20:15",
            "Thursday 10:00–13:00",
            "Thursday 13:00–16:00",
            "Saturday 10:00–13:00",
        ]

    def test_the_selector_offers_none_preferred_possible_and_unavailable(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        assert selector_labels(planning.bruno_client, planning.slug) == [
            "—",
            "Preferred",
            "Possible",
            "Unavailable",
        ]

    def test_each_selector_shows_the_members_own_preference(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        saturday = planning.add_slot("saturday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "preferred")
        chosen(planning, planning.chloe_client, saturday, "unavailable")
        chosen(planning, planning.chloe_client, thursday, "possible")

        assert preferences_shown(planning.bruno_client, planning.slug) == [
            ("Thursday 10:00–13:00", "Preferred"),
            ("Saturday 10:00–13:00", "—"),
        ]
        assert preferences_shown(planning.chloe_client, planning.slug) == [
            ("Thursday 10:00–13:00", "Possible"),
            ("Saturday 10:00–13:00", "Unavailable"),
        ]

    def test_a_manager_sees_their_own_preferences_too(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "unavailable")
        chosen(planning, client, thursday, "possible")

        assert preferences_shown(client, planning.slug) == [("Thursday 10:00–13:00", "Possible")]

    def test_without_a_slot_shows_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        page = availability_page(planning.bruno_client, planning.slug)

        assert collapsed(section_of(page, "My preferences")) == "My preferences None"

    def test_shows_only_the_slots_of_its_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        other = create_association(client, "Repair Café Belleville")
        client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "saturday", "start": "14:00", "end": "18:00"},
        )

        assert preferences_shown(client, planning.slug) == [("Thursday 10:00–13:00", "—")]

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "preferred")
        planning.bruno_client.cookies.set("language", "fr")

        assert preferences_shown(planning.bruno_client, planning.slug, "Mes préférences") == [
            ("Jeudi 10:00–13:00", "Préféré")
        ]
        labels = selector_labels(planning.bruno_client, planning.slug, "Mes préférences")
        assert labels == ["—", "Préféré", "Possible", "Indisponible"]

    def test_without_a_slot_shows_none_in_french(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        page = availability_page(client, planning.slug)

        assert collapsed(section_of(page, "Mes préférences")) == "Mes préférences Aucun"

    def test_signed_out_shows_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        response = new_client().get(f"/association/{planning.slug}/availability")

        assert response.status_code == 200
        assert 'type="password"' in response.text
        assert NAME not in response.text


class TestMyAvailabilityHeader:
    def test_shows_the_association_name_then_my_availability(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        header = text_of(part(availability_page(planning.bruno_client, planning.slug), "header"))

        assert NAME in header
        assert header.index("My availability") > header.index(NAME)
        assert "Bruno" in header

    def test_the_association_name_leads_to_its_schedule(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        header = html.unescape(part(availability_page(client, planning.slug), "header"))

        assert re.search(
            rf'<a[^>]*href="/association/{planning.slug}"[^>]*>\s*{NAME}\s*</a>', header
        )

    def test_the_location_stands_for_the_title(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        main = text_of(without_dialogs(part(availability_page(client, planning.slug), "main")))

        assert "My availability" not in main
        assert NAME not in main

    def test_in_french_the_screen_is_mes_disponibilites(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        header = text_of(part(availability_page(client, planning.slug), "header"))

        assert "Mes disponibilités" in header


class TestUnknownAssociation:
    def test_an_unknown_slug_says_so_with_a_way_to_my_associations(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get(f"/association/{unique_slug()}/availability")

        assert response.status_code == 200
        main = html.unescape(part(response.text, "main"))
        assert UNKNOWN in main
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*My associations\s*</a>', main)
        assert "Page not found" not in response.text

    def test_an_association_of_others_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        response = other_user(new_client).get(f"/association/{planning.slug}/availability")

        assert response.status_code == 200
        assert UNKNOWN in html.unescape(response.text)
        assert NAME not in response.text
        assert "Thursday" not in response.text

    def test_a_deleted_association_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shown(delete_association(client, planning.slug))

        response = planning.bruno_client.get(f"/association/{planning.slug}/availability")

        assert response.status_code == 200
        assert UNKNOWN in html.unescape(response.text)

    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = html.unescape(client.get(f"/association/{unique_slug()}/availability").text)

        assert "Cette association n'existe pas ou vous n'en êtes pas membre." in page


class TestChoosingAPreference:
    @pytest.mark.parametrize(
        ("value", "label"),
        [("preferred", "Preferred"), ("possible", "Possible"), ("unavailable", "Unavailable")],
    )
    def test_saves_it_at_once(
        self, client: Any, new_client: Callable[[], Any], value: str, label: str
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen(planning, planning.bruno_client, thursday, value)

        assert preferences_shown(planning.bruno_client, planning.slug) == [
            ("Thursday 10:00–13:00", label)
        ]
        assert stored(planning) == {("Bruno", THU, value)}

    def test_replaces_the_previous_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "preferred")

        chosen(planning, planning.bruno_client, thursday, "unavailable")

        assert stored(planning) == {("Bruno", THU, "unavailable")}

    def test_none_deletes_it(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "preferred")

        chosen(planning, planning.bruno_client, thursday, "")

        assert preferences_shown(planning.bruno_client, planning.slug) == [
            ("Thursday 10:00–13:00", "—")
        ]
        assert stored(planning) == set()

    def test_none_without_a_preference_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen(planning, planning.bruno_client, thursday, "")

        assert stored(planning) == set()

    def test_sets_only_the_members_own_preference_on_that_slot(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        chosen(planning, planning.chloe_client, thursday, "possible")

        chosen(planning, planning.bruno_client, thursday, "preferred")

        assert stored(planning) == {
            ("Bruno", THU, "preferred"),
            ("Chloé", THU, "possible"),
        }
        assert ("Saturday 10:00–13:00", "—") in preferences_shown(
            planning.bruno_client, planning.slug
        )

    def test_a_manager_sets_their_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen(planning, client, thursday, "possible")

        assert stored(planning) == {("Alice", THU, "possible")}

    @pytest.mark.parametrize("body", [{"value": "maybe"}, {"value": None}, {}])
    def test_a_missing_or_invalid_value_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "preferred")

        response = planning.bruno_client.post(
            f"/association/{planning.slug}/availability/preferences/{thursday['id']}", json=body
        )

        assert GENERIC in shown(response)
        assert stored(planning) == {("Bruno", THU, "preferred")}

    def test_an_unknown_slot_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        response = set_my_preference(planning.bruno_client, planning.slug, UNKNOWN_ID, "preferred")
        text = shown(response)

        assert GENERIC in text
        assert stored(planning) == set()

    def test_a_slot_of_another_association_shows_the_generic_error_and_sets_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville")
        response = client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "saturday", "start": "14:00", "end": "18:00"},
        )
        slot = response.json()

        text = shown(set_my_preference(client, planning.slug, slot["id"], "preferred"))

        assert GENERIC in text
        assert preferences_stored(client, other["slug"]) == set()

    def test_a_non_member_sets_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        set_my_preference(other_user(new_client), planning.slug, thursday["id"], "preferred")

        assert stored(planning) == set()

    def test_signed_out_leads_to_sign_in_and_sets_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        text = shown(set_my_preference(new_client(), planning.slug, thursday["id"], "preferred"))

        assert "window.location" in text
        assert stored(planning) == set()


NOV = "Mon 9 Nov 2037 – Sun 15 Nov 2037"
DEC = "Mon 21 Dec 2037 – Sun 3 Jan 2038"
NOTE = "Always group my registrations in pairs."


def absences_shown(as_client: Any, slug: str) -> list[str]:
    return availability_lines(as_client, slug, "Absences")


def note_shown(as_client: Any, slug: str) -> str:
    """The text of the Note for the managers section, its title included."""
    return availability_section(as_client, slug, "Note for the managers")


def iso_of(shown_date: str) -> str:
    """The ISO date of a date as My availability shows it, e.g. "Mon 9 Nov 2037"."""
    _, day, month, year = shown_date.split()
    return date(int(year), MONTHS.index(month) + 1, int(day)).isoformat()


def absences_stored(planning: Planning) -> set[tuple[str, str, str]]:
    """The absences of Alice, Bruno and Chloé, each as their own My availability lists it: the
    user's id, then its first and last dates. The tests' absences end after today, so all
    show."""
    stored = set()
    for user, as_client in (
        (planning.alice, planning.alice_client),
        (planning.bruno, planning.bruno_client),
        (planning.chloe, planning.chloe_client),
    ):
        for line in absences_shown(as_client, planning.slug):
            first, _, last = line.partition(" – ")
            stored.add((user["id"], iso_of(first), iso_of(last or first)))
    return stored


def notes_stored(planning: Planning) -> dict[str, str]:
    """The note of each member, as a manager's Schedule menu shows them."""
    return notes_offered(planning)


def paris_today() -> date:
    return datetime.now(ZoneInfo("Europe/Paris")).date()


def dialog_titled(page: str, title: str) -> str:
    dialogs = re.findall(r"<dialog.*?</dialog>", part(page, "main"), re.DOTALL)
    found = [d for d in dialogs if re.search(rf"<h2[^>]*>\s*{title}\s*</h2>", d)]
    assert len(found) == 1, page
    return found[0]


def section_html(as_client: Any, slug: str, heading: str) -> str:
    return html.unescape(section_of(availability_page(as_client, slug), heading))


def other_associations_absence(alice_client: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    """Another association of Alice's, with her absence of NOV in it."""
    other = create_association(alice_client, "Repair Café Belleville", unique_slug())
    response = alice_client.post(
        f"/api/associations/{other['id']}/absences",
        json={"first": "2037-11-09", "last": "2037-11-15"},
    )
    assert response.status_code == 201, response.text
    return other, response.json()


class TestAbsences:
    def test_lists_them_by_first_date_with_their_dates(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2037-12-21", "2038-01-03")
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        assert absences_shown(planning.bruno_client, planning.slug) == [NOV, DEC]

    def test_an_absence_of_one_day_shows_one_date(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-09")

        assert absences_shown(planning.bruno_client, planning.slug) == ["Mon 9 Nov 2037"]

    def test_without_an_absence_shows_none(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        assert absences_shown(planning.bruno_client, planning.slug) == []
        assert "None" in availability_section(planning.bruno_client, planning.slug, "Absences")

    def test_lists_only_the_members_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")
        add_absence(planning.chloe_client, planning, "2037-12-21", "2038-01-03")

        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]
        assert absences_shown(planning.chloe_client, planning.slug) == [DEC]
        assert absences_shown(client, planning.slug) == []

    def test_a_manager_sees_their_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        add_absence(client, planning, "2037-11-09", "2037-11-15")

        assert absences_shown(client, planning.slug) == [NOV]

    def test_shows_only_the_absences_of_its_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(client, planning, "2037-12-21", "2038-01-03")
        other, _ = other_associations_absence(client)

        assert absences_shown(client, planning.slug) == [DEC]
        assert absences_shown(client, other["slug"]) == [NOV]

    def test_lists_them_from_those_ending_today_on(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        today = paris_today()
        yesterday = today - timedelta(days=1)
        week_ago = today - timedelta(days=7)
        add_absence(client, planning, "2020-01-06", "2020-01-10")
        add_absence(client, planning, week_ago.isoformat(), yesterday.isoformat())
        add_absence(client, planning, week_ago.isoformat(), today.isoformat())
        add_absence(client, planning, "2037-11-09", "2037-11-15")

        shown_lines = absences_shown(client, planning.slug)

        assert len(shown_lines) == 2
        assert shown_lines[1] == NOV
        assert shown_lines[0].startswith(f"{week_ago:%a} {week_ago.day} {week_ago:%b %Y} – ")

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        add_absence(client, planning, "2037-11-09", "2037-11-15")
        client.cookies.set("language", "fr")

        assert absences_shown(client, planning.slug) == ["lun. 9 nov. 2037 – dim. 15 nov. 2037"]
        main = html.unescape(part(availability_page(client, planning.slug), "main"))
        assert "Ajouter une absence" in main

    def test_without_an_absence_shows_none_in_french(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        assert "Aucune" in availability_section(client, planning.slug, "Absences")


class TestAbsencesDialogs:
    @pytest.mark.parametrize("who", ["manager", "volunteer"])
    def test_shows_add_an_absence(
        self, client: Any, new_client: Callable[[], Any], who: str
    ) -> None:
        planning = Planning(client, new_client)
        as_client = client if who == "manager" else planning.bruno_client

        section = section_of(availability_page(as_client, planning.slug), "Absences")

        assert re.search(r"<button[^>]*>\s*\+\s*Add an absence\s*</button>", section)

    def test_the_add_an_absence_dialog_has_its_title_fields_and_buttons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        page = availability_page(planning.bruno_client, planning.slug)
        form = dialog_titled(page, "Add an absence")

        assert re.search(r'<button[^>]*aria-label="Close"', form)
        assert re.search(r"<label[^>]*>\s*From\b", form)
        assert re.search(r"<label[^>]*>\s*To\b", form)
        assert re.search(r"<button[^>]*>\s*Add absence\s*</button>", form)
        assert re.search(r"<button[^>]*>\s*Cancel\s*</button>", form)

    @pytest.mark.parametrize("who", ["manager", "volunteer"])
    def test_each_absence_has_its_edit_and_delete_icons(
        self, client: Any, new_client: Callable[[], Any], who: str
    ) -> None:
        planning = Planning(client, new_client)
        as_client = client if who == "manager" else planning.bruno_client
        add_absence(as_client, planning, "2037-11-09", "2037-11-15")
        add_absence(as_client, planning, "2037-12-21", "2038-01-03")

        section = section_html(as_client, planning.slug, "Absences")

        assert len(re.findall(r'<button[^>]*aria-label="Edit the absence"', section)) == 2
        assert len(re.findall(r'<button[^>]*aria-label="Delete the absence"', section)) == 2

    def test_the_edit_dialog_is_edit_the_absence_with_save(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        page = availability_page(planning.bruno_client, planning.slug)
        form = dialog_titled(page, "Edit the absence")

        assert re.search(r"<label[^>]*>\s*From\b", form)
        assert re.search(r"<label[^>]*>\s*To\b", form)
        assert re.search(r"<button[^>]*>\s*Save\s*</button>", form)

    @pytest.mark.parametrize(
        ("first", "last", "question"),
        [
            ("2037-11-09", "2037-11-15", f"Delete the absence of {NOV}?"),
            ("2037-11-09", "2037-11-09", "Delete the absence of Mon 9 Nov 2037?"),
        ],
    )
    def test_the_delete_icon_asks_with_its_dates(
        self, client: Any, new_client: Callable[[], Any], first: str, last: str, question: str
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, first, last)

        main = html.unescape(part(availability_page(planning.bruno_client, planning.slug), "main"))

        assert question in main
        assert re.search(r"<button[^>]*>\s*Delete\s*</button>", main)

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        add_absence(client, planning, "2037-11-09", "2037-11-15")
        client.cookies.set("language", "fr")

        main = html.unescape(part(availability_page(client, planning.slug), "main"))

        assert "Ajouter l'absence" in main
        assert 'aria-label="Modifier l\'absence"' in main
        assert "Supprimer l'absence du lun. 9 nov. 2037 – dim. 15 nov. 2037 ?" in main


class TestAddingAnAbsence:
    def test_adds_it_and_the_list_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2037-12-21", "2038-01-03")

        bruno = planning.bruno_client
        text = shown(add_absence_on_screen(bruno, planning.slug, "2037-11-09", "2037-11-15"))

        assert GENERIC not in text
        assert NOV in lines_of(text)
        assert absences_shown(planning.bruno_client, planning.slug) == [NOV, DEC]
        assert (planning.bruno["id"], "2037-11-09", "2037-11-15") in absences_stored(planning)

    def test_accepts_a_single_day(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        text = shown(add_absence_on_screen(client, planning.slug, "2037-11-09", "2037-11-09"))

        assert GENERIC not in text
        assert absences_stored(planning) == {(planning.alice["id"], "2037-11-09", "2037-11-09")}

    def test_adds_only_the_members_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        chloe = planning.chloe_client
        shown(add_absence_on_screen(chloe, planning.slug, "2037-11-09", "2037-11-15"))

        assert absences_stored(planning) == {(planning.chloe["id"], "2037-11-09", "2037-11-15")}
        assert absences_shown(planning.bruno_client, planning.slug) == []

    @pytest.mark.parametrize(
        "body",
        [
            {"last": "2037-11-15"},
            {"first": "2037-11-09"},
            {"first": "", "last": "2037-11-15"},
            {"first": "2037-11-16", "last": "2037-11-15"},
            {"first": "09/11/2037", "last": "2037-11-15"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)

        path = f"/association/{planning.slug}/availability/absences"
        text = shown(planning.bruno_client.post(path, json=body))

        assert GENERIC in text
        assert absences_stored(planning) == set()

    def test_a_non_member_adds_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        add_absence_on_screen(other_user(new_client), planning.slug, "2037-11-09", "2037-11-15")

        assert absences_stored(planning) == set()

    def test_signed_out_leads_to_sign_in_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(add_absence_on_screen(new_client(), planning.slug, "2037-11-09", "2037-11-15"))

        assert "window.location" in text
        assert absences_stored(planning) == set()


class TestEditingAnAbsence:
    def test_saves_it_and_the_list_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        bruno = planning.bruno_client
        absence = add_absence(bruno, planning, "2037-11-09", "2037-11-15")

        text = shown(edit_absence(bruno, planning.slug, absence["id"], "2037-11-10", "2037-11-20"))

        edited = "Tue 10 Nov 2037 – Fri 20 Nov 2037"
        assert GENERIC not in text
        assert edited in lines_of(text)
        assert absences_shown(bruno, planning.slug) == [edited]
        assert absences_stored(planning) == {(planning.bruno["id"], "2037-11-10", "2037-11-20")}

    def test_the_list_stays_by_first_date(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        bruno = planning.bruno_client
        add_absence(bruno, planning, "2037-11-09", "2037-11-15")
        later = add_absence(bruno, planning, "2037-12-21", "2038-01-03")

        shown(edit_absence(bruno, planning.slug, later["id"], "2037-11-02", "2037-11-03"))

        assert absences_shown(bruno, planning.slug) == ["Mon 2 Nov 2037 – Tue 3 Nov 2037", NOV]

    @pytest.mark.parametrize(
        "body",
        [
            {"last": "2037-11-15"},
            {"first": "2037-11-16", "last": "2037-11-15"},
            {"first": "09/11/2037", "last": "2037-11-15"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        path = f"/association/{planning.slug}/availability/absences/{absence['id']}/edit"
        text = shown(planning.bruno_client.post(path, json=body))

        assert GENERIC in text
        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]

    @pytest.mark.parametrize("absence_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_absence_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], absence_id: str
    ) -> None:
        planning = Planning(client, new_client)

        response = edit_absence(client, planning.slug, absence_id, "2037-11-09", "2037-11-15")

        assert GENERIC in shown(response)
        assert absences_stored(planning) == set()

    @pytest.mark.parametrize("who", ["manager", "volunteer"])
    def test_another_members_absence_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], who: str
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")
        other = client if who == "manager" else planning.chloe_client

        response = edit_absence(other, planning.slug, absence["id"], "2037-12-21", "2038-01-03")

        assert GENERIC in shown(response)
        assert absences_stored(planning) == {(planning.bruno["id"], "2037-11-09", "2037-11-15")}

    def test_an_absence_of_another_association_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other, theirs = other_associations_absence(client)

        response = edit_absence(client, planning.slug, theirs["id"], "2037-12-21", "2038-01-03")

        assert GENERIC in shown(response)
        assert absences_shown(client, planning.slug) == []
        assert absences_shown(client, other["slug"]) == [NOV]

    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        zoe = other_user(new_client)
        edit_absence(zoe, planning.slug, absence["id"], "2037-12-21", "2038-01-03")

        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        response = edit_absence(
            new_client(), planning.slug, absence["id"], "2037-12-21", "2038-01-03"
        )

        assert "window.location" in shown(response)
        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]


class TestDeletingAnAbsence:
    def test_deletes_it_and_the_list_leaves_it_out_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        bruno = planning.bruno_client
        nov = add_absence(bruno, planning, "2037-11-09", "2037-11-15")
        add_absence(bruno, planning, "2037-12-21", "2038-01-03")

        text = shown(delete_absence(bruno, planning.slug, nov["id"]))

        assert GENERIC not in text
        assert DEC in lines_of(text)
        assert NOV not in lines_of(text)
        assert absences_shown(bruno, planning.slug) == [DEC]
        assert absences_stored(planning) == {(planning.bruno["id"], "2037-12-21", "2038-01-03")}

    def test_deleting_the_last_one_shows_none(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        text = shown(delete_absence(planning.bruno_client, planning.slug, absence["id"]))

        assert "None" in text
        assert "None" in availability_section(planning.bruno_client, planning.slug, "Absences")

    @pytest.mark.parametrize("absence_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_absence_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], absence_id: str
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        text = shown(delete_absence(planning.bruno_client, planning.slug, absence_id))

        assert GENERIC in text
        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]

    @pytest.mark.parametrize("who", ["manager", "volunteer"])
    def test_another_members_absence_shows_the_generic_error_and_is_kept(
        self, client: Any, new_client: Callable[[], Any], who: str
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")
        other = client if who == "manager" else planning.chloe_client

        text = shown(delete_absence(other, planning.slug, absence["id"]))

        assert GENERIC in text
        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]

    def test_an_absence_of_another_association_is_kept(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other, theirs = other_associations_absence(client)

        text = shown(delete_absence(client, planning.slug, theirs["id"]))

        assert GENERIC in text
        assert absences_shown(client, other["slug"]) == [NOV]

    def test_a_non_member_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        delete_absence(other_user(new_client), planning.slug, absence["id"])

        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]

    def test_signed_out_leads_to_sign_in_and_deletes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        text = shown(delete_absence(new_client(), planning.slug, absence["id"]))

        assert "window.location" in text
        assert absences_shown(planning.bruno_client, planning.slug) == [NOV]


class TestNoteForTheManagers:
    def test_shows_the_note(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        write_note(planning.bruno_client, planning, NOTE)

        assert note_shown(planning.bruno_client, planning.slug) == f"Note for the managers {NOTE}"

    def test_shows_each_line_of_a_note_of_several(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        write_note(planning.bruno_client, planning, "Mornings only.\nNever on Sundays.")

        shown_text = note_shown(planning.bruno_client, planning.slug)

        assert shown_text == "Note for the managers Mornings only. Never on Sundays."

    @pytest.mark.parametrize("text", [None, ""])
    def test_without_a_note_shows_none(
        self, client: Any, new_client: Callable[[], Any], text: str | None
    ) -> None:
        planning = Planning(client, new_client)
        if text is not None:
            write_note(planning.bruno_client, planning, text)

        assert note_shown(planning.bruno_client, planning.slug) == "Note for the managers None"

    def test_shows_only_the_members_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        write_note(planning.bruno_client, planning, NOTE)
        write_note(client, planning, "Mornings only.")

        assert note_shown(planning.chloe_client, planning.slug) == "Note for the managers None"
        assert note_shown(client, planning.slug) == "Note for the managers Mornings only."

    def test_shows_only_the_note_of_its_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        write_note(client, planning, NOTE)

        assert note_shown(client, other["slug"]) == "Note for the managers None"

    def test_escapes_the_note(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        write_note(client, planning, "<b>Pairs</b>")

        page = availability_page(client, planning.slug)

        assert "<b>Pairs</b>" not in page
        assert note_shown(client, planning.slug) == "Note for the managers <b>Pairs</b>"

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        text = availability_section(client, planning.slug, "Note pour les responsables")

        assert text == "Note pour les responsables Aucune"


class TestNoteDialog:
    @pytest.mark.parametrize("who", ["manager", "volunteer"])
    def test_has_its_edit_icon(self, client: Any, new_client: Callable[[], Any], who: str) -> None:
        planning = Planning(client, new_client)
        as_client = client if who == "manager" else planning.bruno_client

        section = section_html(as_client, planning.slug, "Note for the managers")

        assert len(re.findall(r'<button[^>]*aria-label="Edit the note"', section)) == 1

    def test_the_dialog_is_note_for_the_managers_with_a_multi_line_text_and_save(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        page = availability_page(planning.bruno_client, planning.slug)
        form = dialog_titled(page, "Note for the managers")

        assert re.search(r'<button[^>]*aria-label="Close"', form)
        assert re.search(r"<label[^>]*>\s*Text\b.*?<textarea", form, re.DOTALL)
        assert re.search(r"<button[^>]*>\s*Save\s*</button>", form)
        assert re.search(r"<button[^>]*>\s*Cancel\s*</button>", form)

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        page = html.unescape(availability_page(client, planning.slug))
        form = dialog_titled(page, "Note pour les responsables")

        assert 'aria-label="Modifier la note"' in page
        assert re.search(r"<label[^>]*>\s*Texte\b", form)


class TestSavingTheNote:
    def test_saves_it_and_the_screen_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(save_note(planning.bruno_client, planning.slug, NOTE))

        assert GENERIC not in text
        assert NOTE in text
        assert note_shown(planning.bruno_client, planning.slug) == f"Note for the managers {NOTE}"
        assert notes_stored(planning)[planning.bruno["id"]] == NOTE

    def test_keeps_its_lines(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        shown(save_note(planning.bruno_client, planning.slug, "Mornings only.\nNever on Sundays."))

        stored_text = notes_stored(planning)[planning.bruno["id"]]
        assert stored_text == "Mornings only.\nNever on Sundays."

    def test_replaces_the_previous_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        write_note(planning.bruno_client, planning, NOTE)

        shown(save_note(planning.bruno_client, planning.slug, "Mornings only."))

        assert note_shown(planning.bruno_client, planning.slug) == (
            "Note for the managers Mornings only."
        )
        assert notes_stored(planning)[planning.bruno["id"]] == "Mornings only."

    def test_an_empty_text_empties_it_and_shows_none(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        write_note(planning.bruno_client, planning, NOTE)

        text = shown(save_note(planning.bruno_client, planning.slug, ""))

        assert "None" in text
        assert note_shown(planning.bruno_client, planning.slug) == "Note for the managers None"
        assert notes_stored(planning)[planning.bruno["id"]] == ""

    def test_saves_only_the_members_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        shown(save_note(client, planning.slug, NOTE))

        assert notes_stored(planning) == {
            planning.alice["id"]: NOTE,
            planning.bruno["id"]: "",
            planning.chloe["id"]: "",
        }

    @pytest.mark.parametrize("body", [{}, {"text": None}, {"text": 3}])
    def test_a_missing_or_invalid_text_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, Any]
    ) -> None:
        planning = Planning(client, new_client)
        write_note(planning.bruno_client, planning, NOTE)

        path = f"/association/{planning.slug}/availability/note"
        text = shown(planning.bruno_client.post(path, json=body))

        assert GENERIC in text
        assert notes_stored(planning)[planning.bruno["id"]] == NOTE

    def test_a_non_member_saves_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        save_note(other_user(new_client), planning.slug, NOTE)

        assert set(notes_stored(planning).values()) == {""}

    def test_signed_out_leads_to_sign_in_and_saves_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(save_note(new_client(), planning.slug, NOTE))

        assert "window.location" in text
        assert set(notes_stored(planning).values()) == {""}
