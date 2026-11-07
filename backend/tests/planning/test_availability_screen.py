# ruff: noqa: RUF001  (times are written with an en dash, as the screen shows them)
import html
import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import delete_association, unique_slug
from tests.planning.conftest import (
    GENERIC,
    Planning,
    availability_page,
    create_association,
    part,
    section_of,
    set_my_preference,
    shown,
    sign_up,
    text_of,
    unique_email,
    without_dialogs,
)

NAME = "Jardin partagé des Lilas"
UNKNOWN = "This association does not exist or you are not a member."
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


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
    """The preferences of the association, as a manager lists them."""
    response = planning.alice_client.get(planning.path("preferences"))
    assert response.status_code == 200, response.text
    return {(p["user_id"], p["slot_id"], p["value"]) for p in response.json()}


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

        # @dev43:unsure
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

        # @dev43:unsure
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
        assert stored(planning) == {(planning.bruno["id"], thursday["id"], value)}

    def test_replaces_the_previous_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen(planning, planning.bruno_client, thursday, "preferred")

        chosen(planning, planning.bruno_client, thursday, "unavailable")

        assert stored(planning) == {(planning.bruno["id"], thursday["id"], "unavailable")}

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
            (planning.bruno["id"], thursday["id"], "preferred"),
            (planning.chloe["id"], thursday["id"], "possible"),
        }
        assert ("Saturday 10:00–13:00", "—") in preferences_shown(
            planning.bruno_client, planning.slug
        )

    def test_a_manager_sets_their_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen(planning, client, thursday, "possible")

        assert stored(planning) == {(planning.alice["id"], thursday["id"], "possible")}

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
        assert stored(planning) == {(planning.bruno["id"], thursday["id"], "preferred")}

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
        listed = client.get(f"/api/associations/{other['id']}/preferences").json()
        assert listed == []

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
