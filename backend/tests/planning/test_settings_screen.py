# ruff: noqa: RUF001  (times and dates are written with an en dash, as the screen shows them)
import html
import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import delete_association, unique_slug
from tests.planning.conftest import (
    GENERIC,
    Planning,
    add_closure_on_screen,
    add_member,
    add_slot_on_screen,
    availability_page,
    clear_period,
    create_association,
    day_of_week,
    day_shown,
    delete_closure,
    delete_slot,
    edit_closure,
    edit_slot,
    lines_of,
    names_offered,
    part,
    preferences_grid,
    preferences_stored,
    section_of,
    selected_option,
    set_member_preference,
    set_my_preference,
    set_period,
    settings_lines,
    settings_page,
    settings_section,
    shown,
    sign_up,
    text_of,
    unique_email,
    without_dialogs,
)

NAME = "Jardin partagé des Lilas"
UNKNOWN = "This association does not exist or you are not a member."
EXISTS = "This slot already exists."
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
PERIOD = {"first": "2026-11-02", "last": "2026-11-25"}
PERIOD_SHOWN = "Mon 2 Nov 2026 – Wed 25 Nov 2026"
FETE = "Sat 14 Nov 2026 Fête du quartier"
FETES = "Thu 24 Dec 2026 – Fri 1 Jan 2027 Fêtes de fin d'année"


def slots_shown(client: Any, slug: str) -> list[str]:
    """The lines that the Slots section of Schedule settings shows."""
    return lines_of(section_of(settings_page(client, slug), "Slots"))


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


class TestScheduleSettings:
    def test_lists_the_slots_with_their_day_and_times(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("friday", "18:30", "20:15")

        assert slots_shown(client, planning.slug) == [
            "Thursday 10:00–13:00",
            "Friday 18:30–20:15",
        ]

    def test_slots_are_listed_by_weekday_then_start(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        planning.add_slot("thursday", "13:00", "16:00")
        planning.add_slot("monday", "18:00", "20:00")
        planning.add_slot("thursday", "10:00", "13:00")

        assert slots_shown(client, planning.slug) == [
            "Monday 18:00–20:00",
            "Thursday 10:00–13:00",
            "Thursday 13:00–16:00",
            "Saturday 10:00–13:00",
        ]

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

        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        client.cookies.set("language", "fr")

        page = settings_page(client, planning.slug)

        assert "Créneaux" in text_of(part(page, "main"))
        assert lines_of(section_of(page, "Créneaux")) == ["Jeudi 10:00–13:00"]

    def test_signed_out_shows_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        response = new_client().get(f"/association/{planning.slug}/settings")

        assert response.status_code == 200
        assert 'type="password"' in response.text
        assert NAME not in response.text


class TestScheduleSettingsHeader:
    def test_shows_the_association_name_then_schedule_settings(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        header = text_of(part(settings_page(client, planning.slug), "header"))

        assert NAME in header
        assert header.index("Schedule settings") > header.index(NAME)
        assert "Alice" in header

    def test_the_association_name_leads_to_its_schedule(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        header = html.unescape(part(settings_page(client, planning.slug), "header"))

        assert re.search(
            rf'<a[^>]*href="/association/{planning.slug}"[^>]*>\s*{NAME}\s*</a>', header
        )

    def test_the_location_stands_for_the_title(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        main = text_of(without_dialogs(part(settings_page(client, planning.slug), "main")))

        assert "Schedule settings" not in main
        assert NAME not in main

    def test_in_french_the_screen_is_reglages_du_planning(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        header = text_of(part(settings_page(client, planning.slug), "header"))

        assert "Réglages du planning" in header


class TestAsAManager:
    def test_shows_add_a_slot(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        main = part(settings_page(client, planning.slug), "main")

        assert re.search(r"<button[^>]*>\s*\+\s*Add a slot\s*</button>", main)

    def test_the_add_a_slot_dialog_has_its_title_fields_and_buttons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        main = part(settings_page(client, planning.slug), "main")

        dialogs = re.findall(r"<dialog.*?</dialog>", main, re.DOTALL)
        found = [d for d in dialogs if re.search(r"<h2[^>]*>\s*Add a slot\s*</h2>", d)]
        assert len(found) == 1, main
        form = found[0]
        assert re.search(r'<button[^>]*aria-label="Close"', form)
        assert re.search(r"<label[^>]*>\s*Day\b", form)
        assert re.search(r"<label[^>]*>\s*From\b", form)
        assert re.search(r"<label[^>]*>\s*To\b", form)
        for value, label in [("monday", "Monday"), ("thursday", "Thursday"), ("sunday", "Sunday")]:
            assert re.search(rf'<option[^>]*value="{value}"[^>]*>\s*{label}\s*</option>', form)
        assert re.search(r"<button[^>]*>\s*Add slot\s*</button>", form)
        assert re.search(r"<button[^>]*>\s*Cancel\s*</button>", form)

    def test_each_slot_has_its_edit_and_delete_icons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")

        main = without_dialogs(part(settings_page(client, planning.slug), "main"))

        assert len(re.findall(r'<button[^>]*aria-label="Edit the slot"', main)) == 2
        assert len(re.findall(r'<button[^>]*aria-label="Delete the slot"', main)) == 2

    def test_the_edit_dialog_is_edit_the_slot_with_save(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        main = part(settings_page(client, planning.slug), "main")

        dialogs = re.findall(r"<dialog.*?</dialog>", main, re.DOTALL)
        found = [d for d in dialogs if re.search(r"<h2[^>]*>\s*Edit the slot\s*</h2>", d)]
        assert found, main
        assert re.search(r"<button[^>]*>\s*Save\s*</button>", found[0])

    def test_the_delete_icon_asks_with_the_slot(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        main = html.unescape(part(settings_page(client, planning.slug), "main"))

        assert "Delete the slot Thursday 10:00–13:00?" in main
        assert re.search(r"<button[^>]*>\s*Delete\s*</button>", main)

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        client.cookies.set("language", "fr")

        main = html.unescape(part(settings_page(client, planning.slug), "main"))

        assert "Ajouter un créneau" in main
        assert 'aria-label="Modifier le créneau"' in main
        assert 'aria-label="Supprimer le créneau"' in main
        assert "Supprimer le créneau Jeudi 10:00–13:00 ?" in main


class TestAsAVolunteer:
    def test_shows_the_slots_without_add_a_slot_and_icons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        page = html.unescape(settings_page(planning.bruno_client, planning.slug))

        assert lines_of(section_of(page, "Slots")) == ["Thursday 10:00–13:00"]
        assert "Add a slot" not in page
        assert "Add slot" not in page
        assert "Edit the slot" not in page
        assert "Delete the slot" not in page


class TestUnknownAssociation:
    def test_an_unknown_slug_says_so_with_a_way_to_my_associations(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get(f"/association/{unique_slug()}/settings")

        main = html.unescape(part(response.text, "main"))
        assert UNKNOWN in main
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*My associations\s*</a>', main)
        assert "Page not found" not in response.text

    def test_an_association_of_others_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        response = other_user(new_client).get(f"/association/{planning.slug}/settings")

        assert UNKNOWN in html.unescape(response.text)
        assert NAME not in response.text
        assert "Thursday" not in response.text

    def test_a_deleted_association_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shown(delete_association(client, planning.slug))

        response = planning.bruno_client.get(f"/association/{planning.slug}/settings")

        assert UNKNOWN in html.unescape(response.text)

    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = html.unescape(client.get(f"/association/{unique_slug()}/settings").text)

        assert "Cette association n'existe pas ou vous n'en êtes pas membre." in page


class TestAddingASlot:
    def test_adds_it_and_the_list_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        text = shown(add_slot_on_screen(client, planning.slug, "friday", "16:00", "19:00"))

        assert GENERIC not in text
        assert "Friday 16:00–19:00" in lines_of(text)
        assert slots_shown(client, planning.slug) == [
            "Thursday 10:00–13:00",
            "Friday 16:00–19:00",
        ]

    def test_keeps_the_times_to_the_minute(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        shown(add_slot_on_screen(client, planning.slug, "friday", "18:30", "20:15"))

        assert slots_shown(client, planning.slug) == ["Friday 18:30–20:15"]

    def test_the_slot_added_can_be_registered_for(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shown(add_slot_on_screen(client, planning.slug, "thursday", "10:00", "13:00"))

        response = planning.register(
            planning.bruno_client, planning.bruno, day_of_week("thursday"), "10:00", "13:00"
        )

        assert response.status_code == 201, response.text

    def test_a_slot_the_association_already_has_says_so_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        text = shown(add_slot_on_screen(client, planning.slug, "thursday", "10:00", "13:00"))

        assert EXISTS in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_the_same_slot_as_another_associations_is_added(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville")
        client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "thursday", "start": "10:00", "end": "13:00"},
        )

        text = shown(add_slot_on_screen(client, planning.slug, "thursday", "10:00", "13:00"))

        assert EXISTS not in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_the_message_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        client.cookies.set("language", "fr")

        text = shown(add_slot_on_screen(client, planning.slug, "thursday", "10:00", "13:00"))

        assert "Ce créneau existe déjà." in text

    @pytest.mark.parametrize(
        "body",
        [
            {"start": "10:00", "end": "13:00"},
            {"weekday": "someday", "start": "10:00", "end": "13:00"},
            {"weekday": "thursday", "start": "13:00", "end": "10:00"},
            {"weekday": "thursday", "start": "10:00", "end": "10:00"},
            {"weekday": "thursday", "start": "10h", "end": "13:00"},
            {"weekday": "thursday", "start": "10:00"},
            {"weekday": "thursday", "start": "", "end": "13:00"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(client.post(f"/association/{planning.slug}/settings/slots", json=body))

        assert GENERIC in text
        assert slots_shown(client, planning.slug) == []

    def test_a_volunteer_adds_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        add_slot_on_screen(planning.bruno_client, planning.slug, "thursday", "10:00", "13:00")

        assert slots_shown(client, planning.slug) == []

    def test_a_non_member_adds_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        add_slot_on_screen(other_user(new_client), planning.slug, "thursday", "10:00", "13:00")

        assert slots_shown(client, planning.slug) == []

    def test_signed_out_leads_to_sign_in_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(add_slot_on_screen(new_client(), planning.slug, "thursday", "10:00", "13:00"))

        assert "window.location" in text
        assert slots_shown(client, planning.slug) == []


class TestEditingASlot:
    def test_saves_it_and_the_list_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        text = shown(edit_slot(client, planning.slug, slot["id"], "friday", "14:00", "17:30"))

        assert GENERIC not in text
        assert "Friday 14:00–17:30" in lines_of(text)
        assert slots_shown(client, planning.slug) == ["Friday 14:00–17:30"]

    def test_saving_its_own_values_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        text = shown(edit_slot(client, planning.slug, slot["id"], "thursday", "10:00", "13:00"))

        assert EXISTS not in text
        assert GENERIC not in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_as_another_slot_of_the_association_says_so_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        saturday = planning.add_slot("saturday", "10:00", "13:00")

        text = shown(edit_slot(client, planning.slug, saturday["id"], "thursday", "10:00", "13:00"))

        assert EXISTS in text
        assert slots_shown(client, planning.slug) == [
            "Thursday 10:00–13:00",
            "Saturday 10:00–13:00",
        ]

    def test_the_message_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        saturday = planning.add_slot("saturday", "10:00", "13:00")
        client.cookies.set("language", "fr")

        text = shown(edit_slot(client, planning.slug, saturday["id"], "thursday", "10:00", "13:00"))

        assert "Ce créneau existe déjà." in text

    @pytest.mark.parametrize(
        "body",
        [
            {"start": "10:00", "end": "13:00"},
            {"weekday": "someday", "start": "10:00", "end": "13:00"},
            {"weekday": "thursday", "start": "13:00", "end": "10:00"},
            {"weekday": "thursday", "start": "10h", "end": "13:00"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        path = f"/association/{planning.slug}/settings/slots/{slot['id']}/edit"
        text = shown(client.post(path, json=body))

        assert GENERIC in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    @pytest.mark.parametrize("slot_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_slot_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], slot_id: str
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(edit_slot(client, planning.slug, slot_id, "thursday", "10:00", "13:00"))

        assert GENERIC in text
        assert slots_shown(client, planning.slug) == []

    def test_a_slot_of_another_association_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        theirs = client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "saturday", "start": "14:00", "end": "18:00"},
        ).json()

        text = shown(edit_slot(client, planning.slug, theirs["id"], "friday", "10:00", "13:00"))

        assert GENERIC in text
        assert slots_shown(client, planning.slug) == []
        assert slots_shown(client, other["slug"]) == ["Saturday 14:00–18:00"]

    def test_a_volunteer_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        edit_slot(planning.bruno_client, planning.slug, slot["id"], "friday", "10:00", "13:00")

        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        edit_slot(other_user(new_client), planning.slug, slot["id"], "friday", "10:00", "13:00")

        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        response = edit_slot(new_client(), planning.slug, slot["id"], "friday", "10:00", "13:00")

        assert "window.location" in shown(response)
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]


class TestDeletingASlot:
    def test_deletes_it_and_the_list_leaves_it_out_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")

        text = shown(delete_slot(client, planning.slug, thursday["id"]))

        assert GENERIC not in text
        assert lines_of(text) == ["Saturday 10:00–13:00"]
        assert slots_shown(client, planning.slug) == ["Saturday 10:00–13:00"]

    def test_the_slot_can_be_added_again(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        shown(delete_slot(client, planning.slug, slot["id"]))

        text = shown(add_slot_on_screen(client, planning.slug, "thursday", "10:00", "13:00"))

        assert EXISTS not in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    @pytest.mark.parametrize("slot_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_slot_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], slot_id: str
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        text = shown(delete_slot(client, planning.slug, slot_id))

        assert GENERIC in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_a_slot_of_another_association_is_left_as_it_is(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        theirs = client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "saturday", "start": "14:00", "end": "18:00"},
        ).json()

        delete_slot(client, planning.slug, theirs["id"])

        assert slots_shown(client, other["slug"]) == ["Saturday 14:00–18:00"]

    def test_a_volunteer_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        delete_slot(planning.bruno_client, planning.slug, slot["id"])

        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_a_non_member_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        delete_slot(other_user(new_client), planning.slug, slot["id"])

        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_signed_out_leads_to_sign_in_and_deletes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        text = shown(delete_slot(new_client(), planning.slug, slot["id"]))

        assert "window.location" in text
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]


class TestSlotEndpointsRemoved:
    @pytest.mark.parametrize(
        ("method", "body"),
        [
            ("PUT", {"weekday": "friday", "start": "10:00", "end": "13:00"}),
            ("DELETE", None),
        ],
    )
    def test_put_and_delete_api_slot_change_nothing(
        self, client: Any, new_client: Callable[[], Any], method: str, body: dict[str, str] | None
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")

        response = client.request(method, planning.path(f"slots/{slot['id']}"), json=body)

        assert response.status_code in (404, 405)
        assert slots_shown(client, planning.slug) == ["Thursday 10:00–13:00"]

    def test_get_api_slots_lists_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        response = client.get(planning.path("slots"))

        assert response.status_code in (404, 405)


def period_shown(client: Any, slug: str) -> str:
    """The text of the Planning period section, its title included."""
    return settings_section(client, slug, "Planning period")


def closures_shown(client: Any, slug: str) -> list[str]:
    return settings_lines(client, slug, "Closures")


def with_period(planning: Planning, first: str = "2026-11-02", last: str = "2026-11-25") -> None:
    response = planning.alice_client.put(
        planning.path("planning-period"), json={"first": first, "last": last}
    )
    assert response.status_code == 200, response.text


def section_html(client: Any, slug: str, heading: str) -> str:
    return html.unescape(section_of(settings_page(client, slug), heading))


def dialog_titled(page: str, title: str) -> str:
    dialogs = re.findall(r"<dialog.*?</dialog>", part(page, "main"), re.DOTALL)
    found = [d for d in dialogs if re.search(rf"<h2[^>]*>\s*{title}\s*</h2>", d)]
    assert len(found) == 1, page
    return found[0]


class TestPlanningPeriod:
    def test_shows_the_period_from_its_first_to_its_last_date(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        assert PERIOD_SHOWN in period_shown(client, planning.slug)

    def test_without_a_period_shows_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        shown_here = period_shown(client, planning.slug)

        assert "None" in shown_here
        assert "2026" not in shown_here

    def test_shows_the_period_of_its_association_only(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        client.put(f"/api/associations/{other['id']}/planning-period", json=PERIOD)

        assert "None" in period_shown(client, planning.slug)

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        with_period(planning)
        client.cookies.set("language", "fr")

        main = text_of(without_dialogs(part(settings_page(client, planning.slug), "main")))

        assert "lun. 2 nov. 2026 – mer. 25 nov. 2026" in " ".join(main.split())


class TestPlanningPeriodAsAManager:
    def test_has_its_edit_icon_with_or_without_a_period(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        edit = 'aria-label="Edit the period"'
        assert edit in section_html(client, planning.slug, "Planning period")

        with_period(planning)

        assert edit in section_html(client, planning.slug, "Planning period")

    def test_its_delete_icon_shows_only_when_a_period_is_set(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        assert "Clear the period" not in section_html(client, planning.slug, "Planning period")

        with_period(planning)

        clear = 'aria-label="Clear the period"'
        assert clear in section_html(client, planning.slug, "Planning period")

    def test_the_edit_icon_opens_the_dialog_planning_period(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        form = dialog_titled(settings_page(client, planning.slug), "Planning period")

        assert re.search(r'<button[^>]*aria-label="Close"', form)
        assert re.search(r"<label[^>]*>\s*From\b", form)
        assert re.search(r"<label[^>]*>\s*To\b", form)
        assert re.search(r"<button[^>]*>\s*Save\s*</button>", form)
        assert re.search(r"<button[^>]*>\s*Cancel\s*</button>", form)

    def test_the_delete_icon_asks_to_clear_the_planning_period(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        main = html.unescape(part(settings_page(client, planning.slug), "main"))

        assert "Clear the planning period?" in main
        assert re.search(r"<button[^>]*>\s*Clear\s*</button>", main)


class TestPlanningPeriodAsAVolunteer:
    def test_shows_the_period_without_its_icons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        page = html.unescape(settings_page(planning.bruno_client, planning.slug))

        assert PERIOD_SHOWN in period_shown(planning.bruno_client, planning.slug)
        assert "Edit the period" not in page
        assert "Clear the period" not in page
        assert "Clear the planning period?" not in page

    def test_without_a_period_shows_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        assert "None" in period_shown(planning.bruno_client, planning.slug)


class TestSettingThePlanningPeriod:
    def test_sets_it_and_the_screen_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(set_period(client, planning.slug, "2026-11-02", "2026-11-25"))

        assert GENERIC not in text
        assert PERIOD_SHOWN in text
        assert 'aria-label="Clear the period"' in text
        assert PERIOD_SHOWN in period_shown(planning.bruno_client, planning.slug)

    def test_replaces_the_previous_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        shown(set_period(client, planning.slug, "2026-11-30", "2026-12-20"))

        shown_here = period_shown(client, planning.slug)
        assert "Mon 30 Nov 2026 – Sun 20 Dec 2026" in shown_here
        assert PERIOD_SHOWN not in shown_here

    def test_accepts_a_single_day(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        text = shown(set_period(client, planning.slug, "2026-11-02", "2026-11-02"))

        assert GENERIC not in text
        assert "Mon 2 Nov 2026" in period_shown(client, planning.slug)

    def test_the_period_set_counts_the_registrations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        shown(set_period(client, planning.slug, thursday, thursday))

        names = names_offered(client, planning.slug, day_of_week("thursday", 2))
        assert "Bruno (1)" in [text for text, _ in names]

    @pytest.mark.parametrize(
        "body",
        [
            {"first": "2026-11-25", "last": "2026-11-02"},
            {"first": "2026-11-02"},
            {"last": "2026-11-25"},
            {"first": "", "last": "2026-11-25"},
            {"first": "2 Nov", "last": "2026-11-25"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_sets_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(client.post(f"/association/{planning.slug}/settings/period", json=body))

        assert GENERIC in text
        assert "None" in period_shown(client, planning.slug)

    def test_a_volunteer_sets_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        set_period(planning.bruno_client, planning.slug, "2026-11-02", "2026-11-25")

        assert "None" in period_shown(client, planning.slug)

    def test_a_non_member_sets_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        set_period(other_user(new_client), planning.slug, "2026-11-02", "2026-11-25")

        assert "None" in period_shown(client, planning.slug)

    def test_signed_out_leads_to_sign_in_and_sets_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(set_period(new_client(), planning.slug, "2026-11-02", "2026-11-25"))

        assert "window.location" in text
        assert "None" in period_shown(client, planning.slug)


class TestClearingThePlanningPeriod:
    def test_clears_it_and_the_screen_shows_none_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        text = shown(clear_period(client, planning.slug))

        assert GENERIC not in text
        assert PERIOD_SHOWN not in text
        assert "None" in text
        assert "None" in period_shown(client, planning.slug)
        assert "Clear the period" not in section_html(client, planning.slug, "Planning period")

    def test_a_volunteer_clears_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        clear_period(planning.bruno_client, planning.slug)

        assert PERIOD_SHOWN in period_shown(client, planning.slug)

    def test_a_non_member_clears_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        clear_period(other_user(new_client), planning.slug)

        assert PERIOD_SHOWN in period_shown(client, planning.slug)

    def test_signed_out_leads_to_sign_in_and_clears_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        text = shown(clear_period(new_client(), planning.slug))

        assert "window.location" in text
        assert PERIOD_SHOWN in period_shown(client, planning.slug)


class TestPlanningPeriodEndpointsRemoved:
    @pytest.mark.parametrize("method", ["GET", "DELETE"])
    def test_get_and_delete_api_planning_period_leave(
        self, client: Any, new_client: Callable[[], Any], method: str
    ) -> None:
        planning = Planning(client, new_client)
        with_period(planning)

        response = client.request(method, planning.path("planning-period"))

        assert response.status_code in (404, 405)
        assert PERIOD_SHOWN in period_shown(client, planning.slug)


class TestClosures:
    def test_lists_them_by_first_date_with_their_dates_and_label(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-12-24", "2027-01-01", "Fêtes de fin d'année")
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        assert closures_shown(client, planning.slug) == [FETE, FETES]

    def test_a_closure_without_a_label_shows_its_dates_only(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14")

        assert closures_shown(client, planning.slug) == ["Sat 14 Nov 2026"]

    def test_without_a_closure_shows_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        assert closures_shown(client, planning.slug) == []
        assert "None" in settings_section(client, planning.slug, "Closures")

    def test_shows_only_the_closures_of_its_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")
        other = create_association(client, "Repair Café Belleville", unique_slug())
        client.post(
            f"/api/associations/{other['id']}/closures",
            json={"first": "2026-12-24", "last": "2027-01-01", "label": "Fêtes de fin d'année"},
        )

        assert closures_shown(client, planning.slug) == [FETE]

    def test_escapes_the_label(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "<b>Fête</b>")

        page = settings_page(client, planning.slug)

        assert "<b>Fête</b>" not in page
        assert closures_shown(client, planning.slug) == ["Sat 14 Nov 2026 <b>Fête</b>"]

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")
        client.cookies.set("language", "fr")

        main = text_of(without_dialogs(part(settings_page(client, planning.slug), "main")))

        assert "sam. 14 nov. 2026 Fête du quartier" in " ".join(main.split())


class TestClosuresAsAManager:
    def test_shows_add_a_closure(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        main = part(settings_page(client, planning.slug), "main")

        assert re.search(r"<button[^>]*>\s*\+\s*Add a closure\s*</button>", main)

    def test_the_add_a_closure_dialog_has_its_title_fields_and_buttons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        form = dialog_titled(settings_page(client, planning.slug), "Add a closure")

        assert re.search(r'<button[^>]*aria-label="Close"', form)
        assert re.search(r"<label[^>]*>\s*From\b", form)
        assert re.search(r"<label[^>]*>\s*To\b", form)
        assert re.search(r"<label[^>]*>\s*Label\b", form)
        assert re.search(r"<button[^>]*>\s*Add closure\s*</button>", form)
        assert re.search(r"<button[^>]*>\s*Cancel\s*</button>", form)

    def test_each_closure_has_its_edit_and_delete_icons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")
        planning.add_closure("2026-12-24", "2027-01-01")

        section = section_html(client, planning.slug, "Closures")

        assert len(re.findall(r'<button[^>]*aria-label="Edit the closure"', section)) == 2
        assert len(re.findall(r'<button[^>]*aria-label="Delete the closure"', section)) == 2

    def test_the_edit_dialog_is_edit_the_closure_with_save(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        form = dialog_titled(settings_page(client, planning.slug), "Edit the closure")

        assert re.search(r"<label[^>]*>\s*Label\b", form)
        assert re.search(r"<button[^>]*>\s*Save\s*</button>", form)

    @pytest.mark.parametrize(
        ("first", "last", "label", "question"),
        [
            (
                "2026-11-14",
                "2026-11-14",
                "Fête du quartier",
                'Delete the closure "Fête du quartier"?',
            ),
            ("2026-11-14", "2026-11-14", None, "Delete the closure of Sat 14 Nov 2026?"),
            (
                "2026-12-24",
                "2027-01-01",
                None,
                "Delete the closure of Thu 24 Dec 2026 – Fri 1 Jan 2027?",
            ),
        ],
    )
    def test_the_delete_icon_asks_with_the_label_or_else_the_dates(
        self,
        client: Any,
        new_client: Callable[[], Any],
        first: str,
        last: str,
        label: str | None,
        question: str,
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure(first, last, label)

        main = html.unescape(part(settings_page(client, planning.slug), "main"))

        assert question in main
        assert re.search(r"<button[^>]*>\s*Delete\s*</button>", main)


class TestClosuresAsAVolunteer:
    def test_shows_the_closures_without_add_a_closure_and_icons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        page = html.unescape(settings_page(planning.bruno_client, planning.slug))

        assert closures_shown(planning.bruno_client, planning.slug) == [FETE]
        assert "Add a closure" not in page
        assert "Add closure" not in page
        assert "Edit the closure" not in page
        assert "Delete the closure" not in page

    def test_without_a_closure_shows_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        assert "None" in settings_section(planning.bruno_client, planning.slug, "Closures")


class TestAddingAClosure:
    def test_adds_it_and_the_list_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        text = shown(
            add_closure_on_screen(
                client, planning.slug, "2026-12-24", "2027-01-01", "Fêtes de fin d'année"
            )
        )

        assert GENERIC not in text
        assert FETES in lines_of(text)
        assert closures_shown(client, planning.slug) == [FETE, FETES]

    def test_an_empty_label_adds_it_without_a_label(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(add_closure_on_screen(client, planning.slug, "2026-11-14", "2026-11-14", ""))

        assert GENERIC not in text
        assert closures_shown(client, planning.slug) == ["Sat 14 Nov 2026"]
        assert "Delete the closure of Sat 14 Nov 2026?" in html.unescape(
            settings_page(client, planning.slug)
        )

    def test_the_closure_added_closes_the_schedule_on_its_dates(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        saturday = day_of_week("saturday")

        shown(add_closure_on_screen(client, planning.slug, saturday, saturday, "Fête du quartier"))

        shown_on = day_shown(planning.bruno_client, planning.slug, saturday)
        assert shown_on == "Closed Fête du quartier"

    @pytest.mark.parametrize(
        "body",
        [
            {"last": "2026-11-14", "label": ""},
            {"first": "2026-11-14", "label": ""},
            {"first": "", "last": "2026-11-14", "label": ""},
            {"first": "2026-11-15", "last": "2026-11-14", "label": ""},
            {"first": "14/11/2026", "last": "2026-11-14", "label": ""},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(client.post(f"/association/{planning.slug}/settings/closures", json=body))

        assert GENERIC in text
        assert closures_shown(client, planning.slug) == []

    def test_a_volunteer_adds_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        add_closure_on_screen(planning.bruno_client, planning.slug, "2026-11-14", "2026-11-14")

        assert closures_shown(client, planning.slug) == []

    def test_a_non_member_adds_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        add_closure_on_screen(other_user(new_client), planning.slug, "2026-11-14", "2026-11-14")

        assert closures_shown(client, planning.slug) == []

    def test_signed_out_leads_to_sign_in_and_adds_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        response = add_closure_on_screen(new_client(), planning.slug, "2026-11-14", "2026-11-14")
        text = shown(response)

        assert "window.location" in text
        assert closures_shown(client, planning.slug) == []


class TestEditingAClosure:
    def test_saves_it_and_the_list_shows_it_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        text = shown(
            edit_closure(
                client, planning.slug, closure["id"], "2026-11-13", "2026-11-15", "Fête élargie"
            )
        )

        edited = "Fri 13 Nov 2026 – Sun 15 Nov 2026 Fête élargie"
        assert GENERIC not in text
        assert edited in lines_of(text)
        assert closures_shown(client, planning.slug) == [edited]

    def test_an_empty_label_removes_it(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        shown(edit_closure(client, planning.slug, closure["id"], "2026-11-14", "2026-11-14", ""))

        assert closures_shown(client, planning.slug) == ["Sat 14 Nov 2026"]

    def test_the_list_stays_by_first_date(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")
        fetes = planning.add_closure("2026-12-24", "2027-01-01", "Fêtes de fin d'année")

        shown(
            edit_closure(
                client,
                planning.slug,
                fetes["id"],
                "2026-11-02",
                "2026-11-03",
                "Fêtes de fin d'année",
            )
        )

        assert closures_shown(client, planning.slug) == [
            "Mon 2 Nov 2026 – Tue 3 Nov 2026 Fêtes de fin d'année",
            FETE,
        ]

    @pytest.mark.parametrize(
        "body",
        [
            {"last": "2026-11-14", "label": ""},
            {"first": "2026-11-15", "last": "2026-11-14", "label": ""},
            {"first": "14/11/2026", "last": "2026-11-14", "label": ""},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, str]
    ) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        path = f"/association/{planning.slug}/settings/closures/{closure['id']}/edit"
        text = shown(client.post(path, json=body))

        assert GENERIC in text
        assert closures_shown(client, planning.slug) == [FETE]

    @pytest.mark.parametrize("closure_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_closure_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], closure_id: str
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(edit_closure(client, planning.slug, closure_id, "2026-11-14", "2026-11-14"))

        assert GENERIC in text
        assert closures_shown(client, planning.slug) == []

    def test_a_closure_of_another_association_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        theirs = client.post(
            f"/api/associations/{other['id']}/closures",
            json={"first": "2026-11-14", "last": "2026-11-14", "label": "Fête du quartier"},
        ).json()

        text = shown(edit_closure(client, planning.slug, theirs["id"], "2026-12-24", "2026-12-25"))

        assert GENERIC in text
        assert closures_shown(client, planning.slug) == []
        assert closures_shown(client, other["slug"]) == [FETE]

    def test_a_volunteer_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        bruno = planning.bruno_client
        edit_closure(bruno, planning.slug, closure["id"], "2026-12-24", "2026-12-25")

        assert closures_shown(client, planning.slug) == [FETE]

    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        zoe = other_user(new_client)
        edit_closure(zoe, planning.slug, closure["id"], "2026-12-24", "2026-12-25")

        assert closures_shown(client, planning.slug) == [FETE]

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        response = edit_closure(
            new_client(), planning.slug, closure["id"], "2026-12-24", "2026-12-25"
        )

        assert "window.location" in shown(response)
        assert closures_shown(client, planning.slug) == [FETE]


class TestDeletingAClosure:
    def test_deletes_it_and_the_list_leaves_it_out_at_once(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        fete = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")
        planning.add_closure("2026-12-24", "2027-01-01", "Fêtes de fin d'année")

        text = shown(delete_closure(client, planning.slug, fete["id"]))

        assert GENERIC not in text
        assert FETES in lines_of(text)
        assert "Fête du quartier" not in text
        assert closures_shown(client, planning.slug) == [FETES]

    def test_deleting_the_last_one_shows_none(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        fete = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        text = shown(delete_closure(client, planning.slug, fete["id"]))

        assert "None" in text
        assert "None" in settings_section(client, planning.slug, "Closures")

    @pytest.mark.parametrize("closure_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_closure_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], closure_id: str
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        text = shown(delete_closure(client, planning.slug, closure_id))

        assert GENERIC in text
        assert closures_shown(client, planning.slug) == [FETE]

    def test_a_closure_of_another_association_is_left_as_it_is(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        theirs = client.post(
            f"/api/associations/{other['id']}/closures",
            json={"first": "2026-11-14", "last": "2026-11-14", "label": "Fête du quartier"},
        ).json()

        delete_closure(client, planning.slug, theirs["id"])

        assert closures_shown(client, other["slug"]) == [FETE]

    def test_a_volunteer_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        delete_closure(planning.bruno_client, planning.slug, closure["id"])

        assert closures_shown(client, planning.slug) == [FETE]

    def test_a_non_member_deletes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        delete_closure(other_user(new_client), planning.slug, closure["id"])

        assert closures_shown(client, planning.slug) == [FETE]

    def test_signed_out_leads_to_sign_in_and_deletes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        text = shown(delete_closure(new_client(), planning.slug, closure["id"]))

        assert "window.location" in text
        assert closures_shown(client, planning.slug) == [FETE]


class TestClosureEndpointsRemoved:
    @pytest.mark.parametrize(
        ("method", "body"),
        [("PUT", {"first": "2026-12-24", "last": "2026-12-25", "label": None}), ("DELETE", None)],
    )
    def test_put_and_delete_api_closure_change_nothing(
        self, client: Any, new_client: Callable[[], Any], method: str, body: dict[str, Any] | None
    ) -> None:
        planning = Planning(client, new_client)
        closure = planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        response = client.request(method, planning.path(f"closures/{closure['id']}"), json=body)

        assert response.status_code in (404, 405)
        assert closures_shown(client, planning.slug) == [FETE]

    def test_get_api_closures_lists_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

        response = client.get(planning.path("closures"))

        assert response.status_code in (404, 405)


THU = "Thu 10:00–13:00"
SAT = "Sat 10:00–13:00"


def chosen_for(
    planning: Planning, member: dict[str, Any], slot: dict[str, Any], value: str
) -> None:
    """Alice chooses `value` for `member` and `slot` in Members' preferences."""
    alice = planning.alice_client
    text = shown(set_member_preference(alice, planning.slug, slot["id"], member["id"], value))
    assert GENERIC not in text, text


def own_preference(as_client: Any, slug: str) -> str:
    """The label that the first selector of the user's own My preferences shows."""
    section = section_of(availability_page(as_client, slug), "My preferences")
    select = re.search(r"<select.*?</select>", section, re.DOTALL)
    assert select, section
    return selected_option(select[0])[1]


def stored(planning: Planning) -> set[tuple[str, str, str]]:
    return preferences_stored(planning.alice_client, planning.slug)


class TestMembersPreferences:
    def test_one_row_per_member_and_one_column_per_slot(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")

        assert preferences_grid(client, planning.slug) == (
            [THU, SAT],
            [("Alice", ["—", "—"]), ("Bruno", ["—", "—"]), ("Chloé", ["—", "—"])],
        )

    def test_each_selector_shows_the_members_preference_on_the_slot(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        saturday = planning.add_slot("saturday", "10:00", "13:00")
        chosen_mine(planning, client, thursday, "preferred")
        chosen_mine(planning, planning.bruno_client, thursday, "possible")
        chosen_mine(planning, planning.bruno_client, saturday, "unavailable")
        chosen_mine(planning, planning.chloe_client, saturday, "preferred")

        assert preferences_grid(client, planning.slug)[1] == [
            ("Alice", ["Preferred", "—"]),
            ("Bruno", ["Possible", "Unavailable"]),
            ("Chloé", ["—", "Preferred"]),
        ]

    def test_the_selector_offers_none_preferred_possible_and_unavailable(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        section = section_of(settings_page(client, planning.slug), "Members' preferences")
        select = re.search(r"<select.*?</select>", section, re.DOTALL)
        assert select, section
        labels = re.findall(r"<option[^>]*>(.*?)</option>", select[0], re.DOTALL)
        assert [" ".join(label.split()) for label in labels] == [
            "—",
            "Preferred",
            "Possible",
            "Unavailable",
        ]

    def test_its_rows_follow_the_order_of_members(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        added = add_member(client, planning.id, "Zoé", unique_email("Zoe"), "manager")
        assert added.status_code == 201
        added = add_member(client, planning.id, "anna", unique_email("Anna"))
        assert added.status_code == 201

        rows = preferences_grid(client, planning.slug)[1]

        assert [name for name, _ in rows] == ["Alice", "Zoé", "anna", "Bruno", "Chloé"]

    def test_its_columns_follow_the_order_of_slots(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        planning.add_slot("thursday", "13:00", "16:00")
        planning.add_slot("monday", "18:30", "20:15")
        planning.add_slot("thursday", "10:00", "13:00")

        assert preferences_grid(client, planning.slug)[0] == [
            "Mon 18:30–20:15",
            THU,
            "Thu 13:00–16:00",
            SAT,
        ]

    def test_without_a_slot_shows_none(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        section = settings_section(client, planning.slug, "Members' preferences")

        assert section == "Members' preferences None"

    def test_shows_only_the_members_and_slots_of_its_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        other = create_association(client, "Repair Café Belleville", unique_slug())
        client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "saturday", "start": "14:00", "end": "18:00"},
        )
        assert add_member(client, other["id"], "Zoé", unique_email("Zoe")).status_code == 201

        assert preferences_grid(client, planning.slug) == (
            [THU],
            [("Alice", ["—"]), ("Bruno", ["—"]), ("Chloé", ["—"])],
        )

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, thursday, "preferred")
        client.cookies.set("language", "fr")

        page = settings_page(client, planning.slug)

        section = section_of(page, "Préférences des membres")
        assert "jeu. 10:00–13:00" in " ".join(text_of(section).split())
        assert "Préféré" in text_of(section)
        assert "Indisponible" in text_of(section)

    def test_without_a_slot_shows_none_in_french(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        section = settings_section(client, planning.slug, "Préférences des membres")

        assert section == "Préférences des membres Aucun"

    def test_a_volunteer_does_not_see_it(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.chloe_client, thursday, "unavailable")

        page = html.unescape(settings_page(planning.bruno_client, planning.slug))

        assert "Members' preferences" not in page
        assert "<select" not in without_dialogs(part(page, "main"))


def chosen_mine(planning: Planning, as_client: Any, slot: dict[str, Any], value: str) -> None:
    """The user chooses `value` for `slot` in their own My preferences."""
    text = shown(set_my_preference(as_client, planning.slug, slot["id"], value))
    assert GENERIC not in text, text


class TestChoosingAMembersPreference:
    @pytest.mark.parametrize(
        ("value", "label"),
        [("preferred", "Preferred"), ("possible", "Possible"), ("unavailable", "Unavailable")],
    )
    def test_saves_it_at_once(
        self, client: Any, new_client: Callable[[], Any], value: str, label: str
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen_for(planning, planning.bruno, thursday, value)

        assert stored(planning) == {("Bruno", THU, value)}
        assert own_preference(planning.bruno_client, planning.slug) == label

    def test_replaces_the_previous_one(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, thursday, "preferred")

        chosen_for(planning, planning.bruno, thursday, "unavailable")

        assert stored(planning) == {("Bruno", THU, "unavailable")}

    def test_none_deletes_it(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, thursday, "preferred")

        chosen_for(planning, planning.bruno, thursday, "")

        assert stored(planning) == set()
        assert own_preference(planning.bruno_client, planning.slug) == "—"

    def test_none_without_a_preference_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen_for(planning, planning.bruno, thursday, "")

        assert stored(planning) == set()

    def test_sets_only_that_members_preference_on_that_slot(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        chosen_mine(planning, planning.chloe_client, thursday, "possible")

        chosen_for(planning, planning.bruno, thursday, "preferred")

        assert stored(planning) == {("Bruno", THU, "preferred"), ("Chloé", THU, "possible")}

    def test_a_manager_sets_their_own(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        chosen_for(planning, planning.alice, thursday, "possible")

        assert stored(planning) == {("Alice", THU, "possible")}

    @pytest.mark.parametrize("body", [{"value": "maybe"}, {"value": None}, {}])
    def test_a_missing_or_invalid_value_shows_the_generic_error_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, thursday, "preferred")

        response = client.post(
            f"/association/{planning.slug}/settings/preferences/{thursday['id']}"
            f"/{planning.bruno['id']}",
            json=body,
        )

        assert GENERIC in shown(response)
        assert stored(planning) == {("Bruno", THU, "preferred")}

    def test_an_unknown_slot_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        response = set_member_preference(
            client, planning.slug, UNKNOWN_ID, planning.bruno["id"], "preferred"
        )

        assert GENERIC in shown(response)
        assert stored(planning) == set()

    def test_a_slot_of_another_association_shows_the_generic_error_and_sets_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville", unique_slug())
        response = client.post(
            f"/api/associations/{other['id']}/slots",
            json={"weekday": "saturday", "start": "14:00", "end": "18:00"},
        )
        slot = response.json()

        for member in (planning.alice, planning.bruno):
            response = set_member_preference(
                client, planning.slug, slot["id"], member["id"], "preferred"
            )
            assert GENERIC in shown(response)

        assert preferences_stored(client, other["slug"]) == set()

    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        outsider = sign_up(new_client(), "Zoé", unique_email("Zoe"))

        for user_id in (outsider["id"], UNKNOWN_ID):
            response = set_member_preference(
                client, planning.slug, thursday["id"], user_id, "preferred"
            )
            assert GENERIC in shown(response)

        assert stored(planning) == set()

    def test_a_volunteer_sets_nothing_and_sees_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.chloe_client, thursday, "possible")

        for value in ("preferred", ""):
            response = set_member_preference(
                planning.bruno_client, planning.slug, thursday["id"], planning.chloe["id"], value
            )
            assert GENERIC in shown(response)

        assert stored(planning) == {("Chloé", THU, "possible")}

    def test_a_non_member_sets_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        set_member_preference(
            other_user(new_client), planning.slug, thursday["id"], planning.bruno["id"], "preferred"
        )

        assert stored(planning) == set()

    def test_signed_out_leads_to_sign_in_and_sets_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")

        response = set_member_preference(
            new_client(), planning.slug, thursday["id"], planning.bruno["id"], "preferred"
        )

        assert "window.location" in shown(response)
        assert stored(planning) == set()


class TestPreferenceAndSlot:
    def test_deleting_a_slot_deletes_its_preferences(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursday = planning.add_slot("thursday", "10:00", "13:00")
        saturday = planning.add_slot("saturday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, thursday, "preferred")
        chosen_mine(planning, planning.bruno_client, saturday, "possible")

        planning.delete_slot(thursday)

        assert stored(planning) == {("Bruno", SAT, "possible")}

    def test_editing_a_slot_keeps_its_preferences(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, slot, "preferred")

        planning.edit_slot(slot, "friday", "14:00", "17:00")

        assert stored(planning) == {("Bruno", "Fri 14:00–17:00", "preferred")}

    def test_a_slot_added_again_has_no_preferences(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, slot, "preferred")
        planning.delete_slot(slot)

        planning.add_slot("thursday", "10:00", "13:00")

        assert stored(planning) == set()


class TestPreferenceEndpointsRemoved:
    @pytest.mark.parametrize(
        ("method", "body"), [("PUT", {"value": "preferred"}), ("DELETE", None)]
    )
    def test_put_and_delete_api_preference_change_nothing(
        self, client: Any, new_client: Callable[[], Any], method: str, body: dict[str, Any] | None
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, slot, "possible")

        path = planning.path(f"preferences/{slot['id']}/{planning.bruno['id']}")
        response = client.request(method, path, json=body)

        assert response.status_code in (404, 405)
        assert stored(planning) == {("Bruno", THU, "possible")}

    def test_get_api_preferences_lists_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        chosen_mine(planning, planning.bruno_client, slot, "possible")

        response = client.get(planning.path("preferences"))

        assert response.status_code in (404, 405)
