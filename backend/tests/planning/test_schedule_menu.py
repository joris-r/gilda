# ruff: noqa: RUF001  (menu titles are written with a middle dot and times with an en dash)
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from tests.planning.conftest import (
    GENERIC,
    WEEKDAYS,
    Planning,
    add_absence,
    add_absence_of,
    add_member,
    add_slot,
    cancel_registration,
    confirm_registration,
    create_association,
    day_in,
    day_label,
    day_of_week,
    day_shown,
    headings_of,
    names_offered,
    open_menu,
    opened_weeks,
    propose,
    save_note,
    schedule_entries,
    schedule_shown,
    set_member_preference,
    set_period,
    shown,
    sign_up,
    sign_up_for,
    text_of,
    unique_email,
    write_note,
)

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
TAKEN = "Someone took this slot in the meantime."


def thursday_planning(client: Any, new_client: Callable[[], Any]) -> tuple[Planning, str]:
    """A planning with a slot on Thursday 10:00-13:00, and next week's Thursday."""
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    return planning, day_of_week("thursday")


def proposed_to_bruno(client: Any, new_client: Callable[[], Any]) -> tuple[Planning, str, Any]:
    """Alice has proposed next week's Thursday to Bruno."""
    planning, thursday = thursday_planning(client, new_client)
    registration = planning.registered(client, planning.bruno, thursday, "10:00", "13:00")
    return planning, thursday, registration


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


def menu_text(as_client: Any, slug: str, day: str) -> str:
    """What the menu of the occurrence of `day` from 10:00 to 13:00 shows, its spaces
    collapsed."""
    return " ".join(text_of(shown(open_menu(as_client, slug, day, "10:00", "13:00"))).split())


def today_in_paris() -> date:
    return datetime.now(ZoneInfo("Europe/Paris")).date()


class TestMenu:
    def test_is_titled_with_its_day_and_times(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        assert f"{day_label(thursday)} · 10–13" in text

    def test_the_title_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.bruno_client.cookies.set("language", "fr")

        with time_machine.travel(datetime(2026, 11, 9, 9, 0, tzinfo=UTC), tick=False):
            text = menu_text(planning.bruno_client, planning.slug, "2026-11-12")

        assert "jeu. 12 nov. · 10–13" in text
        assert "S'inscrire" in text

    def test_a_free_occurrence_offers_sign_up(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        for as_client in (planning.bruno_client, planning.alice_client):
            text = menu_text(as_client, planning.slug, thursday)
            assert "Sign up" in text
            assert "Confirm" not in text
            assert "Cancel registration" not in text

    def test_a_cancelled_registration_offers_sign_up(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.chloe_client, planning.chloe, thursday, "10:00", "13:00"
        )
        planning.cancel(planning.chloe_client, registration)

        for as_client in (planning.bruno_client, planning.chloe_client):
            text = menu_text(as_client, planning.slug, thursday)
            assert "Sign up" in text
            assert "Cancel registration" not in text

    def test_the_users_own_confirmed_registration_offers_cancel_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        assert "Cancel registration…" in text
        assert "Sign up" not in text
        assert "Confirm" not in text

    def test_a_managers_own_registration_offers_cancel_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(client, planning.alice, thursday, "10:00", "13:00")

        text = menu_text(client, planning.slug, thursday)

        assert "Cancel registration…" in text
        assert "Sign up" not in text

    def test_the_users_own_proposed_registration_offers_confirm_and_cancel_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        assert "Confirm" in text
        assert "Cancel registration…" in text
        assert "Sign up" not in text

    def test_another_members_registration_offers_a_volunteer_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)

        text = menu_text(planning.chloe_client, planning.slug, thursday)

        assert f"{day_label(thursday)} · 10–13" in text
        for absent in ["Sign up", "Confirm", "Cancel registration"]:
            assert absent not in text

    def test_an_obsolete_proposed_registration_offers_cancel_registration_but_not_confirm(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)
        planning.delete_slot(planning.slots[0])

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        assert f"{day_label(thursday)} · 10–13" in text
        assert "Cancel registration…" in text
        assert "Confirm" not in text
        assert "Sign up" not in text

    def test_an_obsolete_confirmed_registration_offers_cancel_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
        planning.delete_slot(planning.slots[0])

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        assert "Cancel registration…" in text

    def test_cancel_registration_asks_before_cancelling(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        assert "Cancel this registration?" in text
        assert "Yes, cancel" in text
        assert "Keep it" in text

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)
        planning.bruno_client.cookies.set("language", "fr")

        text = menu_text(planning.bruno_client, planning.slug, thursday)

        for present in ["Confirmer", "Annuler l'inscription…", "Annuler cette inscription ?"]:
            assert present in text

    @pytest.mark.parametrize(
        "body",
        [
            {"start": "10:00", "end": "13:00"},
            {"date": "12/11/2026", "start": "10:00", "end": "13:00"},
            {"date": "2026-11-12", "start": "", "end": "13:00"},
        ],
    )
    def test_a_missing_or_invalid_field_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, Any]
    ) -> None:
        planning, _ = thursday_planning(client, new_client)

        text = shown(client.post(f"/association/{planning.slug}/menu", json=body))

        assert GENERIC in text
        assert "Sign up" not in text

    def test_a_non_member_is_offered_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        response = open_menu(other_user(new_client), planning.slug, thursday, "10:00", "13:00")

        assert "Sign up" not in response.text

    def test_signed_out_leads_to_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday = thursday_planning(client, new_client)

        text = shown(open_menu(new_client(), planning.slug, thursday, "10:00", "13:00"))

        assert "window.location" in text
        assert "Sign up" not in text


def free_thursday(client: Any, new_client: Callable[[], Any]) -> tuple[Planning, str]:
    """A planning with a slot on Thursday 10:00-13:00, and the Thursday two weeks ahead, which
    holds no registration."""
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    return planning, day_of_week("thursday", 2)


def texts_offered(as_client: Any, slug: str, day: str) -> list[str]:
    """The text of each name the menu of the occurrence of `day` offers, in order."""
    return [text for text, _ in names_offered(as_client, slug, day)]


def icons_of(as_client: Any, slug: str, day: str, name: str) -> list[str]:
    """The text of each icon of the name `name` in the menu of the occurrence of `day`."""
    found = [icons for text, icons in names_offered(as_client, slug, day) if text == name]
    assert len(found) == 1, (name, names_offered(as_client, slug, day))
    return found[0]


def prefer(planning: Planning, user: dict[str, Any], value: str) -> None:
    """Alice sets the preference of `user` for the first slot in Members' preferences."""
    response = set_member_preference(
        planning.alice_client, planning.slug, planning.slots[0]["id"], user["id"], value
    )
    assert GENERIC not in shown(response)


def with_period(planning: Planning) -> None:
    """Sets the planning period from next week's Monday to the Sunday three weeks ahead."""
    response = set_period(
        planning.alice_client, planning.slug, day_of_week("monday", 1), day_of_week("sunday", 3)
    )
    assert GENERIC not in shown(response)


class TestManagersMenu:
    def test_a_free_occurrence_offers_the_members_display_names(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)

        text = menu_text(client, planning.slug, thursday)

        assert "Sign up" in text
        assert texts_offered(client, planning.slug, thursday) == ["Alice", "Bruno", "Chloé"]

    def test_a_cancelled_registration_offers_the_members_display_names(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        registration = planning.registered(
            planning.chloe_client, planning.chloe, thursday, "10:00", "13:00"
        )
        planning.cancel(planning.chloe_client, registration)

        assert texts_offered(client, planning.slug, thursday) == ["Alice", "Bruno", "Chloé"]

    def test_a_volunteer_is_offered_no_names(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)

        assert names_offered(planning.bruno_client, planning.slug, thursday) == []
        text = menu_text(planning.bruno_client, planning.slug, thursday)
        assert "Sign up" in text
        assert "Alice" not in text
        assert "Chloé" not in text

    def test_a_taken_occurrence_offers_no_names(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)

        assert names_offered(client, planning.slug, thursday) == []

    def test_another_members_proposed_registration_offers_confirm_and_cancel_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)

        text = menu_text(client, planning.slug, thursday)

        assert "Confirm" in text
        assert "Cancel registration…" in text
        assert "Sign up" not in text

    def test_another_members_confirmed_registration_offers_cancel_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        text = menu_text(client, planning.slug, thursday)

        assert "Cancel registration…" in text
        assert "Confirm" not in text
        assert "Sign up" not in text

    def test_another_members_obsolete_registration_offers_cancel_registration_but_not_confirm(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)
        planning.delete_slot(planning.slots[0])

        text = menu_text(client, planning.slug, thursday)

        assert "Cancel registration…" in text
        assert "Confirm" not in text
        assert names_offered(client, planning.slug, thursday) == []

    def test_a_member_of_another_association_is_not_offered(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        other = create_association(client, "Repair Café Belleville")
        zoe_email = unique_email("Zoe")
        sign_up(new_client(), "Zoé", zoe_email)
        add_member(client, other["slug"], "Zoé", zoe_email)

        assert texts_offered(client, planning.slug, thursday) == ["Alice", "Bruno", "Chloé"]


class TestRegistrationCount:
    def test_without_a_planning_period_no_count_is_shown(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        planning.registered(
            planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
        )

        assert texts_offered(client, planning.slug, thursday) == ["Alice", "Bruno", "Chloé"]

    def test_each_name_is_followed_by_its_count(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        with_period(planning)

        assert set(texts_offered(client, planning.slug, thursday)) == {
            "Alice (0)",
            "Bruno (0)",
            "Chloé (0)",
        }

    def test_r15_counts_proposed_and_confirmed_registrations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        with_period(planning)
        planning.registered(
            planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
        )
        planning.registered(client, planning.bruno, day_of_week("saturday", 1), "10:00", "13:00")
        planning.registered(client, planning.chloe, day_of_week("saturday", 2), "10:00", "13:00")

        assert set(texts_offered(client, planning.slug, thursday)) == {
            "Alice (0)",
            "Bruno (2)",
            "Chloé (1)",
        }

    def test_r15_does_not_count_cancelled_registrations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        with_period(planning)
        registration = planning.registered(
            planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
        )
        planning.cancel(planning.bruno_client, registration)

        assert "Bruno (0)" in texts_offered(client, planning.slug, thursday)

    def test_r15_does_not_count_registrations_outside_the_planning_period(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        for weeks_ahead in (1, 2, 3):
            day = day_of_week("thursday", weeks_ahead)
            planning.registered(planning.bruno_client, planning.bruno, day, "10:00", "13:00")
        thursday = day_of_week("thursday", 2)
        assert GENERIC not in shown(set_period(client, planning.slug, thursday, thursday))

        offered = texts_offered(client, planning.slug, day_of_week("saturday", 2))

        assert "Bruno (1)" in offered

    def test_r15_does_not_count_obsolete_registrations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        thursdays = planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        with_period(planning)
        planning.registered(
            planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
        )
        planning.delete_slot(thursdays)

        offered = texts_offered(client, planning.slug, day_of_week("saturday", 2))

        assert "Bruno (0)" in offered

    def test_r15_counts_only_the_associations_registrations(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        with_period(planning)
        other = Planning(new_client(), new_client)
        other.add_slot("thursday", "10:00", "13:00")
        add_member(other.alice_client, other.slug, "Bruno", planning.bruno["email"])
        other.registered(
            other.alice_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
        )

        assert "Bruno (0)" in texts_offered(client, planning.slug, thursday)


class TestR27:
    def test_names_are_sorted_by_preference(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        planning._volunteer(new_client, "David")
        prefer(planning, planning.alice, "unavailable")
        prefer(planning, planning.bruno, "possible")
        prefer(planning, planning.chloe, "preferred")

        assert texts_offered(client, planning.slug, thursday) == [
            "Chloé",
            "Bruno",
            "David",
            "Alice",
        ]

    def test_the_preference_is_for_the_occurrences_slot(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, _ = free_thursday(client, new_client)
        prefer(planning, planning.bruno, "unavailable")
        planning.add_slot("saturday", "10:00", "13:00")

        offered = texts_offered(client, planning.slug, day_of_week("saturday", 2))

        assert offered == ["Alice", "Bruno", "Chloé"]

    def test_absent_members_come_last_whatever_their_preference(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        prefer(planning, planning.alice, "unavailable")
        prefer(planning, planning.bruno, "preferred")
        add_absence(planning.bruno_client, planning, thursday, thursday)

        assert texts_offered(client, planning.slug, thursday) == ["Chloé", "Alice", "Bruno"]

    def test_then_by_fewest_registrations(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday = free_thursday(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        with_period(planning)
        planning.registered(client, planning.alice, day_of_week("thursday", 1), "10:00", "13:00")
        planning.registered(client, planning.chloe, day_of_week("saturday", 1), "10:00", "13:00")
        planning.registered(client, planning.chloe, day_of_week("saturday", 2), "10:00", "13:00")

        assert texts_offered(client, planning.slug, thursday) == [
            "Bruno (0)",
            "Alice (1)",
            "Chloé (2)",
        ]

    def test_fewest_registrations_also_orders_absent_members(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        with_period(planning)
        planning.registered(client, planning.alice, day_of_week("thursday", 1), "10:00", "13:00")
        add_absence(client, planning, thursday, thursday)
        add_absence(planning.chloe_client, planning, thursday, thursday)
        prefer(planning, planning.alice, "preferred")

        assert texts_offered(client, planning.slug, thursday) == [
            "Bruno (0)",
            "Chloé (0)",
            "Alice (1)",
        ]

    def test_then_by_display_name(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday = free_thursday(client, new_client)
        prefer(planning, planning.chloe, "possible")
        prefer(planning, planning.alice, "possible")

        assert texts_offered(client, planning.slug, thursday) == ["Alice", "Chloé", "Bruno"]


class TestAbsenceIcon:
    def test_an_absent_member_has_an_absence_icon(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        icons = icons_of(client, planning.slug, "2037-11-12", "Bruno")

        assert icons == ["Absent Mon 9 Nov 2037 – Sun 15 Nov 2037"]

    def test_a_one_day_absence_shows_one_date(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        add_absence(planning.bruno_client, planning, "2037-11-12", "2037-11-12")

        icons = icons_of(client, planning.slug, "2037-11-12", "Bruno")

        assert icons == ["Absent Thu 12 Nov 2037"]

    def test_the_icon_shows_the_absence_covering_the_occurrences_date(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        add_absence(planning.bruno_client, planning, "2037-11-02", "2037-11-06")
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")
        add_absence(planning.bruno_client, planning, "2037-11-16", "2037-11-20")

        icons = icons_of(client, planning.slug, "2037-11-12", "Bruno")

        assert icons == ["Absent Mon 9 Nov 2037 – Sun 15 Nov 2037"]

    def test_an_absence_not_covering_the_date_shows_no_icon(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        add_absence(planning.bruno_client, planning, "2037-11-13", "2037-11-15")
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-11")

        assert icons_of(client, planning.slug, "2037-11-12", "Bruno") == []

    def test_an_absence_in_another_association_shows_no_icon(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        other = create_association(client, "Repair Café Belleville")
        add_absence_of(client, other, "2037-11-09", "2037-11-15")

        assert icons_of(client, planning.slug, "2037-11-12", "Alice") == []

    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")
        client.cookies.set("language", "fr")

        icons = icons_of(client, planning.slug, "2037-11-12", "Bruno")

        assert icons == ["Absent du lun. 9 nov. 2037 au dim. 15 nov. 2037"]


NOTE = "Always group my registrations in pairs."


class TestNoteIcon:
    def test_a_member_with_a_note_has_a_note_icon(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        write_note(planning.bruno_client, planning, NOTE)

        assert icons_of(client, planning.slug, thursday, "Bruno") == [NOTE]
        assert icons_of(client, planning.slug, thursday, "Chloé") == []

    def test_the_note_keeps_its_lines(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday = free_thursday(client, new_client)
        write_note(planning.bruno_client, planning, "Mornings only.\nNever on Sundays.")

        icons = icons_of(client, planning.slug, thursday, "Bruno")

        assert icons == ["Mornings only.\nNever on Sundays."]

    @pytest.mark.parametrize("text", ["", "   "])
    def test_an_empty_note_or_one_of_only_spaces_shows_no_icon(
        self, client: Any, new_client: Callable[[], Any], text: str
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        write_note(planning.bruno_client, planning, text)

        assert icons_of(client, planning.slug, thursday, "Bruno") == []

    def test_a_note_in_another_association_shows_no_icon(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = free_thursday(client, new_client)
        other = create_association(client, "Repair Café Belleville")
        assert GENERIC not in shown(save_note(client, other["slug"], NOTE))

        assert icons_of(client, planning.slug, thursday, "Alice") == []

    def test_an_absent_member_with_a_note_has_both_icons(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        add_absence(planning.bruno_client, planning, "2037-11-12", "2037-11-12")
        write_note(planning.bruno_client, planning, NOTE)

        icons = icons_of(client, planning.slug, "2037-11-12", "Bruno")

        assert sorted(icons) == sorted(["Absent Thu 12 Nov 2037", NOTE])


class TestSignUp:
    def test_r5_a_volunteer_signing_up_is_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        text = shown(sign_up_for(planning.bruno_client, planning.slug, thursday, "10:00", "13:00"))

        assert GENERIC not in text
        assert day_in(schedule_entries(text), thursday) == "[Bruno]"
        assert day_shown(client, planning.slug, thursday) == "[Bruno]"

    def test_r5_a_manager_signing_up_is_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        text = shown(sign_up_for(client, planning.slug, thursday, "10:00", "13:00"))

        assert day_in(schedule_entries(text), thursday) == "[Alice]"
        assert day_shown(planning.bruno_client, planning.slug, thursday) == "[Alice]"

    def test_shows_the_weeks_shown(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        late_thursday = day_of_week("thursday", 7)
        weeks = {"from": day_of_week("monday", -1), "to": day_of_week("sunday", 8)}

        text = shown(
            sign_up_for(
                planning.bruno_client, planning.slug, late_thursday, "10:00", "13:00", weeks
            )
        )

        entries = schedule_entries(text)
        assert len(headings_of(entries)) == 10
        assert day_in(entries, late_thursday) == "[Bruno]"

    def test_r4_a_taken_occurrence_says_someone_took_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.chloe_client, planning.chloe, thursday, "10:00", "13:00")

        text = shown(sign_up_for(planning.bruno_client, planning.slug, thursday, "10:00", "13:00"))

        assert TAKEN in text
        assert GENERIC not in text
        assert day_shown(client, planning.slug, thursday) == "[Chloé]"

    def test_r4_also_when_it_holds_a_proposed_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, _ = proposed_to_bruno(client, new_client)

        text = shown(sign_up_for(planning.chloe_client, planning.slug, thursday, "10:00", "13:00"))

        assert TAKEN in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"

    def test_r4_the_taken_message_follows_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.chloe_client, planning.chloe, thursday, "10:00", "13:00")
        planning.bruno_client.cookies.set("language", "fr")

        text = shown(sign_up_for(planning.bruno_client, planning.slug, thursday, "10:00", "13:00"))

        assert "Quelqu'un a pris ce créneau entre-temps." in text

    def test_r4_an_occurrence_whose_registration_was_cancelled_takes_a_new_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.chloe_client, planning.chloe, thursday, "10:00", "13:00"
        )
        planning.cancel(planning.chloe_client, registration)

        text = shown(sign_up_for(planning.bruno_client, planning.slug, thursday, "10:00", "13:00"))

        assert day_in(schedule_entries(text), thursday) == "[Bruno]"

    def test_r6_an_occurrence_before_today_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, _ = thursday_planning(client, new_client)
        past = day_of_week("thursday", -1)

        text = shown(sign_up_for(planning.bruno_client, planning.slug, past, "10:00", "13:00"))

        assert GENERIC in text
        assert day_shown(client, planning.slug, past) == "[]"

    def test_r6_today_is_not_before_today(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        today = today_in_paris()
        planning.add_slot(WEEKDAYS[today.weekday()], "23:00", "23:30")

        text = shown(
            sign_up_for(planning.bruno_client, planning.slug, today.isoformat(), "23:00", "23:30")
        )

        assert GENERIC not in text
        assert day_in(schedule_entries(text), today.isoformat()) == "[Bruno]"

    @pytest.mark.parametrize(
        ("now", "day", "taken"),
        [
            # Summer: 00:30 on 1 July in Paris (UTC+2), still 30 June in UTC.
            (datetime(2026, 6, 30, 22, 30, tzinfo=UTC), date(2026, 6, 30), False),
            (datetime(2026, 6, 30, 22, 30, tzinfo=UTC), date(2026, 7, 1), True),
            # Winter: 00:30 on 1 January in Paris (UTC+1), still 31 December in UTC.
            (datetime(2026, 12, 31, 23, 30, tzinfo=UTC), date(2026, 12, 31), False),
            (datetime(2026, 12, 31, 23, 30, tzinfo=UTC), date(2027, 1, 1), True),
            # 23:30 on 31 December in Paris: still today.
            (datetime(2026, 12, 31, 22, 30, tzinfo=UTC), date(2026, 12, 31), True),
        ],
    )
    def test_r11_r6_today_is_in_the_associations_timezone(
        self, client: Any, new_client: Callable[[], Any], now: datetime, day: date, taken: bool
    ) -> None:
        with time_machine.travel(now, tick=False):
            planning = Planning(client, new_client)
            planning.add_slot(WEEKDAYS[day.weekday()], "10:00", "13:00")
            monday = day.toordinal() - day.weekday()
            weeks = {
                "from": date.fromordinal(monday - 7).isoformat(),
                "to": date.fromordinal(monday + 13).isoformat(),
            }

            text = shown(
                sign_up_for(
                    planning.bruno_client, planning.slug, day.isoformat(), "10:00", "13:00", weeks
                )
            )

            assert (GENERIC not in text) == taken, text
            assert day_shown(client, planning.slug, day.isoformat()) == (
                "[Bruno]" if taken else "[]"
            )

    @pytest.mark.parametrize(
        ("weekday", "start", "end"),
        [
            ("friday", "10:00", "13:00"),
            ("thursday", "10:00", "12:00"),
            ("thursday", "09:00", "13:00"),
        ],
    )
    def test_no_occurrence_matching_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], weekday: str, start: str, end: str
    ) -> None:
        planning, _ = thursday_planning(client, new_client)

        text = shown(
            sign_up_for(planning.bruno_client, planning.slug, day_of_week(weekday), start, end)
        )

        assert GENERIC in text
        assert "Bruno" not in str(schedule_shown(client, planning.slug))

    def test_a_closure_date_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.add_closure(thursday, thursday)

        text = shown(sign_up_for(planning.bruno_client, planning.slug, thursday, "10:00", "13:00"))

        assert GENERIC in text
        assert "Bruno" not in str(schedule_shown(client, planning.slug))

    def test_a_slot_of_another_association_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        other = create_association(client, "Repair Café Belleville")
        add_slot(client, other, "thursday", "10:00", "13:00")

        text = shown(sign_up_for(client, planning.slug, day_of_week("thursday"), "10:00", "13:00"))

        assert GENERIC in text

    @pytest.mark.parametrize("missing", ["date", "start", "end"])
    def test_a_missing_field_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], missing: str
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        body = {
            "date": thursday,
            "start": "10:00",
            "end": "13:00",
            "from": day_of_week("monday", -1),
            "to": day_of_week("sunday", 4),
        }
        del body[missing]

        text = shown(client.post(f"/association/{planning.slug}/sign-up", json=body))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[]"

    def test_a_non_member_registers_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        response = sign_up_for(other_user(new_client), planning.slug, thursday, "10:00", "13:00")

        assert "Week" not in response.text
        assert day_shown(client, planning.slug, thursday) == "[]"

    def test_signed_out_leads_to_sign_in_and_registers_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        text = shown(sign_up_for(new_client(), planning.slug, thursday, "10:00", "13:00"))

        assert "window.location" in text
        assert day_shown(client, planning.slug, thursday) == "[]"


def propose_bruno(as_client: Any, planning: Planning, day: str) -> Any:
    """Clicks Bruno's name in the menu of the occurrence of `day` from 10:00 to 13:00."""
    return propose(as_client, planning.slug, planning.bruno["id"], day, "10:00", "13:00")


class TestPropose:
    def test_r5_a_member_proposed_the_occurrence_gets_proposed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        text = shown(propose_bruno(client, planning, thursday))

        assert GENERIC not in text
        assert day_in(schedule_entries(text), thursday) == "[Bruno ?]"
        assert day_shown(planning.bruno_client, planning.slug, thursday) == "[Bruno ?]"

    def test_r5_a_manager_registering_themself_by_their_own_name_gets_confirmed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        alice = planning.alice["id"]
        text = shown(propose(client, planning.slug, alice, thursday, "10:00", "13:00"))

        assert day_in(schedule_entries(text), thursday) == "[Alice]"
        assert day_shown(planning.bruno_client, planning.slug, thursday) == "[Alice]"

    def test_r5_only_a_manager_proposes(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday = thursday_planning(client, new_client)

        response = propose(
            planning.bruno_client, planning.slug, planning.chloe["id"], thursday, "10:00", "13:00"
        )

        assert GENERIC in shown(response)
        assert day_shown(client, planning.slug, thursday) == "[]"

    def test_shows_the_weeks_shown(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, _ = thursday_planning(client, new_client)
        late_thursday = day_of_week("thursday", 7)
        weeks = {"from": day_of_week("monday", -1), "to": day_of_week("sunday", 8)}

        text = shown(
            propose(
                client, planning.slug, planning.bruno["id"], late_thursday, "10:00", "13:00", weeks
            )
        )

        entries = schedule_entries(text)
        assert len(headings_of(entries)) == 10
        assert day_in(entries, late_thursday) == "[Bruno ?]"

    def test_r4_a_taken_occurrence_says_someone_took_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.registered(planning.chloe_client, planning.chloe, thursday, "10:00", "13:00")

        text = shown(propose_bruno(client, planning, thursday))

        assert TAKEN in text
        assert GENERIC not in text
        assert day_shown(client, planning.slug, thursday) == "[Chloé]"

    def test_r4_an_occurrence_whose_registration_was_cancelled_takes_a_new_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.chloe_client, planning.chloe, thursday, "10:00", "13:00"
        )
        planning.cancel(planning.chloe_client, registration)

        text = shown(propose_bruno(client, planning, thursday))

        assert day_in(schedule_entries(text), thursday) == "[Bruno ?]"

    def test_r6_an_occurrence_before_today_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, _ = thursday_planning(client, new_client)
        past = day_of_week("thursday", -1)

        text = shown(propose_bruno(client, planning, past))

        assert GENERIC in text
        assert day_shown(client, planning.slug, past) == "[]"

    def test_a_closure_date_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        planning.add_closure(thursday, thursday, "Fête")

        text = shown(propose_bruno(client, planning, thursday))

        assert GENERIC in text
        assert "Bruno" not in str(schedule_shown(client, planning.slug))

    @pytest.mark.parametrize("who", ["non-member", "unknown", "invalid"])
    def test_a_user_who_is_not_a_member_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], who: str
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        zoe = sign_up(new_client(), "Zoé", unique_email("Zoe"))
        user_id = {"non-member": zoe["id"], "unknown": UNKNOWN_ID, "invalid": "not-an-id"}[who]

        text = shown(propose(client, planning.slug, user_id, thursday, "10:00", "13:00"))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[]"

    @pytest.mark.parametrize("missing", ["user_id", "date", "start", "end", "from"])
    def test_a_missing_field_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], missing: str
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        body = {
            "user_id": planning.bruno["id"],
            "date": thursday,
            "start": "10:00",
            "end": "13:00",
            **opened_weeks(),
        }
        del body[missing]

        text = shown(client.post(f"/association/{planning.slug}/propose", json=body))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[]"

    def test_a_non_member_registers_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        response = propose(
            other_user(new_client), planning.slug, planning.bruno["id"], thursday, "10:00", "13:00"
        )

        assert "Week" not in response.text
        assert day_shown(client, planning.slug, thursday) == "[]"

    def test_signed_out_leads_to_sign_in_and_registers_no_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)

        response = propose(
            new_client(), planning.slug, planning.bruno["id"], thursday, "10:00", "13:00"
        )

        assert "window.location" in shown(response)
        assert day_shown(client, planning.slug, thursday) == "[]"


class TestConfirm:
    def test_r7_the_registered_user_confirms_a_proposed_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        text = shown(confirm_registration(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC not in text
        assert day_in(schedule_entries(text), thursday) == "[Bruno]"
        assert day_shown(client, planning.slug, thursday) == "[Bruno]"

    def test_r7_a_manager_confirms_another_members_proposed_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        text = shown(confirm_registration(client, planning.slug, registration["id"]))

        assert day_in(schedule_entries(text), thursday) == "[Bruno]"

    def test_r7_nobody_else_confirms(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        text = shown(confirm_registration(planning.chloe_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"

    def test_r7_a_confirmed_registration_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
        )

        text = shown(confirm_registration(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC in text

    def test_r7_a_cancelled_registration_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)
        planning.cancel(planning.bruno_client, registration)

        text = shown(confirm_registration(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[~~Bruno~~]"

    def test_r7_an_obsolete_registration_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)
        planning.delete_slot(planning.slots[0])

        for as_client in (planning.bruno_client, client):
            text = shown(confirm_registration(as_client, planning.slug, registration["id"]))
            assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ? obsolete]"

    @pytest.mark.parametrize("registration_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_registration_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], registration_id: str
    ) -> None:
        planning, _ = thursday_planning(client, new_client)

        text = shown(confirm_registration(client, planning.slug, registration_id))

        assert GENERIC in text

    def test_a_registration_of_another_association_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)
        other = create_association(client, "Repair Café Belleville")

        text = shown(confirm_registration(client, other["slug"], registration["id"]))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        text = shown(confirm_registration(new_client(), planning.slug, registration["id"]))

        assert "window.location" in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"

    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        confirm_registration(other_user(new_client), planning.slug, registration["id"])

        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"


class TestCancelRegistration:
    def test_r7_the_registered_user_cancels(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
        )

        text = shown(cancel_registration(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC not in text
        assert day_in(schedule_entries(text), thursday) == "[~~Bruno~~]"
        assert day_shown(client, planning.slug, thursday) == "[~~Bruno~~]"

    def test_r7_the_registered_user_cancels_a_proposed_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        text = shown(cancel_registration(planning.bruno_client, planning.slug, registration["id"]))

        assert day_in(schedule_entries(text), thursday) == "[~~Bruno~~]"

    def test_r7_a_manager_cancels_another_members_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
        )

        text = shown(cancel_registration(client, planning.slug, registration["id"]))

        assert day_in(schedule_entries(text), thursday) == "[~~Bruno~~]"

    def test_r7_an_obsolete_registration_can_be_cancelled(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, _, registration = proposed_to_bruno(client, new_client)
        planning.delete_slot(planning.slots[0])

        text = shown(cancel_registration(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC not in text
        assert "Bruno" not in str(schedule_entries(text))
        assert "Bruno" not in str(schedule_shown(client, planning.slug))

    def test_r7_another_volunteer_cannot_cancel(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday = thursday_planning(client, new_client)
        registration = planning.registered(
            planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
        )

        text = shown(cancel_registration(planning.chloe_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno]"

    def test_r7_a_cancelled_registration_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, _, registration = proposed_to_bruno(client, new_client)
        planning.cancel(client, registration)

        text = shown(cancel_registration(client, planning.slug, registration["id"]))

        assert GENERIC in text

    @pytest.mark.parametrize("registration_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_registration_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], registration_id: str
    ) -> None:
        planning, _ = thursday_planning(client, new_client)

        text = shown(cancel_registration(client, planning.slug, registration_id))

        assert GENERIC in text

    def test_a_registration_of_another_association_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)
        other = create_association(client, "Repair Café Belleville")

        text = shown(cancel_registration(client, other["slug"], registration["id"]))

        assert GENERIC in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        text = shown(cancel_registration(new_client(), planning.slug, registration["id"]))

        assert "window.location" in text
        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"

    def test_a_non_member_changes_nothing(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning, thursday, registration = proposed_to_bruno(client, new_client)

        cancel_registration(other_user(new_client), planning.slug, registration["id"])

        assert day_shown(client, planning.slug, thursday) == "[Bruno ?]"
