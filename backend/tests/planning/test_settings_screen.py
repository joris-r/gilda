# ruff: noqa: RUF001  (slot times are written with an en dash, as the screen shows them)
import html
import re
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import delete_association, unique_slug
from tests.planning.conftest import (
    GENERIC,
    Planning,
    add_slot_on_screen,
    create_association,
    day_of_week,
    delete_slot,
    edit_slot,
    shown,
    sign_up,
    unique_email,
)

NAME = "Jardin partagé des Lilas"
UNKNOWN = "This association does not exist or you are not a member."
EXISTS = "This slot already exists."
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def part(page: str, tag: str) -> str:
    match = re.search(rf"<{tag}[ >].*</{tag}>", page, re.DOTALL)
    assert match, f"no {tag} in {page}"
    return match.group(0)


def text_of(fragment: str) -> str:
    """What a piece of HTML shows, without its tags and attributes."""
    return html.unescape(re.sub(r"<[^>]+>", " ", fragment))


def without_dialogs(fragment: str) -> str:
    return re.sub(r"<dialog.*?</dialog>", "", fragment, flags=re.DOTALL)


def lines_of(fragment: str) -> list[str]:
    """The text of each list item outside the dialogs, in order, its spaces collapsed."""
    items = re.findall(r"<li.*?</li>", without_dialogs(fragment), re.DOTALL)
    return [" ".join(text_of(item).split()) for item in items]


def settings_page(client: Any, slug: str) -> str:
    response = client.get(f"/association/{slug}/settings")
    assert response.status_code == 200
    return str(response.text)


def slots_shown(client: Any, slug: str) -> list[str]:
    """The lines that Schedule settings shows in main."""
    return lines_of(part(settings_page(client, slug), "main"))


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
        assert lines_of(part(page, "main")) == ["Jeudi 10:00–13:00"]

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

        assert lines_of(part(page, "main")) == ["Thursday 10:00–13:00"]
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
