# ruff: noqa: RUF001  (times and ranges are written with an en dash)
import re
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
import time_machine

from tests.core.conftest import Listed, listed, my_associations_listed
from tests.planning.conftest import (
    GENERIC,
    WEEKDAYS,
    Planning,
    create_association,
    shown,
    sign_up,
    unique_email,
)

NAME = "Jardin partagé des Lilas"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"

# Wednesday 4 November 2026, 10:00 in Paris.
NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
TODAY = date(2026, 11, 4)

SHORT_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
NO_LONGER = ": this slot no longer takes place."


def day(offset: int) -> str:
    """The date `offset` days after today."""
    return (TODAY + timedelta(days=offset)).isoformat()


def label(offset: int, start: str = "10:00", end: str = "13:00") -> str:
    """How a registration `offset` days after today shows its date and times."""
    shown_day = TODAY + timedelta(days=offset)
    weekday = SHORT_WEEKDAYS[shown_day.weekday()]
    return f"{weekday} {shown_day.day} {MONTHS[shown_day.month - 1]}, {start}–{end}"


def confirmed_line(offset: int, start: str = "10:00", end: str = "13:00") -> str:
    return f"{label(offset, start, end)} Bruno"


def proposed_line(offset: int) -> str:
    return f"{label(offset)} Bruno ? Confirm"


def obsolete_line(offset: int, start: str = "10:00", end: str = "13:00") -> str:
    return f"{label(offset, start, end)} Bruno{NO_LONGER} OK"


@pytest.fixture
def clock() -> Iterator[time_machine.Traveller]:
    with time_machine.travel(NOW, tick=False) as traveller:
        yield traveller


@pytest.fixture
def planning(clock: time_machine.Traveller, client: Any, new_client: Callable[[], Any]) -> Planning:
    """Alice's association, open every day from 10:00 to 13:00; Bruno volunteers in it."""
    planning = Planning(client, new_client)
    for weekday in WEEKDAYS:
        planning.add_slot(weekday, "10:00", "13:00")
    return planning


def set_period(planning: Planning, first: int, last: int, as_client: Any = None) -> None:
    response = (as_client or planning.alice_client).put(
        planning.path("planning-period"), json={"first": day(first), "last": day(last)}
    )
    assert response.status_code == 200, response.text


def entry(as_client: Any, name: str = NAME) -> Listed:
    """The association named `name` as My associations lists it."""
    found = [item for item in my_associations_listed(as_client) if item.name == name]
    assert len(found) == 1, found
    return found[0]


def bruno_lines(planning: Planning) -> list[str]:
    return entry(planning.bruno_client).lines


def upcoming(planning: Planning) -> list[str]:
    return [line for line in bruno_lines(planning) if NO_LONGER not in line]


def obsolete(planning: Planning) -> list[str]:
    return [line for line in bruno_lines(planning) if NO_LONGER in line]


def confirmed(planning: Planning, offset: int, start: str = "10:00", end: str = "13:00") -> Any:
    """Bruno signs up himself."""
    return planning.registered(planning.bruno_client, planning.bruno, day(offset), start, end)


def proposed(planning: Planning, offset: int) -> Any:
    """Alice proposes the occurrence to Bruno."""
    return planning.registered(planning.alice_client, planning.bruno, day(offset), "10:00", "13:00")


def slot_on(offset: int, planning: Planning, start: str, end: str) -> dict[str, Any]:
    """Adds a slot on the weekday `offset` days after today."""
    weekday = WEEKDAYS[(TODAY + timedelta(days=offset)).weekday()]
    return planning.add_slot(weekday, start, end)


def reminds(planning: Planning) -> bool:
    return "No registration yet for the planning period" in entry(planning.bruno_client).text


def confirm_on_summary(as_client: Any, slug: str, registration_id: str) -> Any:
    """Clicks "Confirm" on a registration on My associations."""
    return as_client.post(f"/association/{slug}/summary/{registration_id}/confirm", json={})


def ok_on_summary(as_client: Any, slug: str, registration_id: str) -> Any:
    """Clicks "OK" on an obsolete registration on My associations."""
    return as_client.post(f"/association/{slug}/summary/{registration_id}/cancel", json={})


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


class TestMyAssociations:
    def test_example(self, planning: Planning) -> None:
        set_period(planning, -2, 21)
        confirmed(planning, 1)
        proposed(planning, 10)
        confirmed(planning, 8)
        planning.add_closure(day(8), day(8))
        repair = create_association(planning.bruno_client, "Repair Café Belleville")
        response = planning.bruno_client.put(
            f"/api/associations/{repair['id']}/planning-period",
            json={"first": day(-2), "last": day(21)},
        )
        assert response.status_code == 200, response.text
        create_association(planning.bruno_client, "Atelier vélo")

        jardin = entry(planning.bruno_client)
        assert jardin.lines == [obsolete_line(8), confirmed_line(1), proposed_line(10)]
        assert "No upcoming registration." not in jardin.text
        assert "No registration yet" not in jardin.text

        repair_cafe = entry(planning.bruno_client, "Repair Café Belleville")
        assert repair_cafe.lines == []
        assert "No registration yet for the planning period, 2–25 Nov." in repair_cafe.text
        assert "Choose your slots" in repair_cafe.text
        assert "No upcoming registration." not in repair_cafe.text

        atelier = entry(planning.bruno_client, "Atelier vélo")
        assert atelier.lines == []
        assert "No upcoming registration." in atelier.text
        assert "Choose your slots" not in atelier.text

    def test_in_french(self, planning: Planning) -> None:
        confirmed(planning, 1)
        proposed(planning, 10)
        confirmed(planning, 8)
        planning.add_closure(day(8), day(8))
        repair = create_association(planning.bruno_client, "Repair Café Belleville")
        response = planning.bruno_client.put(
            f"/api/associations/{repair['id']}/planning-period",
            json={"first": day(-2), "last": day(21)},
        )
        assert response.status_code == 200, response.text
        create_association(planning.bruno_client, "Atelier vélo")
        planning.bruno_client.cookies.set("language", "fr")

        assert entry(planning.bruno_client).lines == [
            "jeu. 12 nov., 10:00–13:00 Bruno : ce créneau n'a plus lieu. OK",
            "jeu. 5 nov., 10:00–13:00 Bruno",
            "sam. 14 nov., 10:00–13:00 Bruno ? Confirmer",
        ]
        repair_cafe = entry(planning.bruno_client, "Repair Café Belleville").text
        assert "Aucune inscription pour la période de planning, 2–25 nov." in repair_cafe
        assert "Choisir mes créneaux" in repair_cafe
        assert "Aucune inscription à venir." in entry(planning.bruno_client, "Atelier vélo").text

    def test_shows_only_the_signed_in_users_registrations(self, planning: Planning) -> None:
        planning.registered(planning.chloe_client, planning.chloe, day(2), "10:00", "13:00")
        planning.registered(planning.alice_client, planning.chloe, day(3), "10:00", "13:00")
        planning.add_closure(day(3), day(3))

        assert bruno_lines(planning) == []
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_a_confirmed_registration_has_no_mark_and_no_action(self, planning: Planning) -> None:
        confirmed(planning, 1)

        assert bruno_lines(planning) == [confirmed_line(1)]

    def test_escapes_the_display_name(self, client: Any, new_client: Callable[[], Any]) -> None:
        sign_up(client, "<b>Alice</b>", unique_email("Alice"))
        association = create_association(client)
        planning_path = f"/api/associations/{association['id']}"
        weekday = WEEKDAYS[date.today().weekday()]
        slot = client.post(
            f"{planning_path}/slots", json={"weekday": weekday, "start": "10:00", "end": "13:00"}
        )
        assert slot.status_code == 201, slot.text
        user = client.get("/api/session").json()
        response = client.post(
            f"{planning_path}/registrations",
            json={
                "user_id": user["id"],
                "date": (date.today() + timedelta(days=7)).isoformat(),
                "start": "10:00",
                "end": "13:00",
            },
        )
        assert response.status_code == 201, response.text

        page = client.get("/").text

        assert "<b>Alice</b>" not in page
        assert entry(client).lines[0].endswith(" <b>Alice</b>")


class TestR31:
    def test_obsolete_registrations_come_first(self, planning: Planning) -> None:
        confirmed(planning, 1)
        confirmed(planning, 5)
        planning.add_closure(day(5), day(5))

        assert bruno_lines(planning) == [obsolete_line(5), confirmed_line(1)]

    def test_a_removed_slot_makes_its_registrations_obsolete(self, planning: Planning) -> None:
        slot = slot_on(2, planning, "14:00", "16:00")
        confirmed(planning, 2, "14:00", "16:00")
        planning.delete_slot(slot)

        assert obsolete(planning) == [obsolete_line(2, "14:00", "16:00")]

    def test_a_closure_makes_its_registrations_obsolete(self, planning: Planning) -> None:
        confirmed(planning, 3)
        proposed(planning, 4)
        confirmed(planning, 6)
        planning.add_closure(day(3), day(4))

        assert obsolete(planning) == [obsolete_line(3), obsolete_line(4)]
        assert upcoming(planning) == [confirmed_line(6)]

    def test_a_proposed_one_has_ok_but_not_confirm(self, planning: Planning) -> None:
        proposed(planning, 4)
        planning.add_closure(day(4), day(4))

        assert bruno_lines(planning) == [obsolete_line(4)]

    def test_an_edited_slot_makes_its_registrations_obsolete(self, planning: Planning) -> None:
        slot = slot_on(2, planning, "14:00", "16:00")
        confirmed(planning, 2, "14:00", "16:00")
        planning.edit_slot(slot, slot["weekday"], "15:00", "17:00")

        assert obsolete(planning) == [obsolete_line(2, "14:00", "16:00")]

    def test_whatever_their_date(self, planning: Planning) -> None:
        set_period(planning, 0, 10)
        confirmed(planning, 60)
        planning.add_closure(day(60), day(60))

        assert obsolete(planning) == [obsolete_line(60)]

    def test_sorted_by_date_then_start(self, planning: Planning) -> None:
        slot_on(2, planning, "08:00", "09:00")
        confirmed(planning, 2)
        proposed(planning, 1)
        confirmed(planning, 2, "08:00", "09:00")
        planning.add_closure(day(1), day(2))

        assert obsolete(planning) == [
            obsolete_line(1),
            obsolete_line(2, "08:00", "09:00"),
            obsolete_line(2),
        ]

    def test_today_is_included_and_earlier_dates_are_not(
        self, planning: Planning, clock: time_machine.Traveller
    ) -> None:
        confirmed(planning, 1)
        confirmed(planning, 2)
        planning.add_closure(day(1), day(2))

        clock.shift(timedelta(days=2))

        assert obsolete(planning) == [obsolete_line(2)]

    def test_cancelled_registrations_are_not_listed(self, planning: Planning) -> None:
        registration = confirmed(planning, 2)
        planning.add_closure(day(2), day(2))
        planning.cancel(planning.bruno_client, registration)

        assert bruno_lines(planning) == []
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_only_the_signed_in_users_registrations(self, planning: Planning) -> None:
        planning.registered(planning.chloe_client, planning.chloe, day(2), "10:00", "13:00")
        planning.add_closure(day(2), day(2))

        assert bruno_lines(planning) == []
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_with_only_obsolete_ones_no_upcoming_registration(self, planning: Planning) -> None:
        confirmed(planning, 2)
        planning.add_closure(day(2), day(2))

        assert "No upcoming registration." in entry(planning.bruno_client).text


class TestR12:
    def test_obsolete_registrations_are_not_upcoming(self, planning: Planning) -> None:
        slot = slot_on(2, planning, "14:00", "16:00")
        confirmed(planning, 2, "14:00", "16:00")
        planning.delete_slot(slot)

        assert upcoming(planning) == []
        assert obsolete(planning) == [obsolete_line(2, "14:00", "16:00")]

    def test_cancelled_registrations_are_not_shown(self, planning: Planning) -> None:
        registration = confirmed(planning, 2)
        planning.cancel(planning.bruno_client, registration)

        assert bruno_lines(planning) == []
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_sorted_by_date_then_start(self, planning: Planning) -> None:
        slot_on(2, planning, "08:00", "09:00")
        confirmed(planning, 2)
        proposed(planning, 1)
        confirmed(planning, 2, "08:00", "09:00")

        assert upcoming(planning) == [
            proposed_line(1),
            confirmed_line(2, "08:00", "09:00"),
            confirmed_line(2),
        ]

    def test_today_is_included(self, planning: Planning) -> None:
        confirmed(planning, 0)
        proposed(planning, 1)

        assert upcoming(planning) == [confirmed_line(0), proposed_line(1)]

    def test_registrations_before_today_are_not_shown(
        self, planning: Planning, clock: time_machine.Traveller
    ) -> None:
        confirmed(planning, 1)
        proposed(planning, 2)
        confirmed(planning, 3)

        clock.shift(timedelta(days=3))

        assert upcoming(planning) == [confirmed_line(3)]

    def test_every_proposed_one_shows_whatever_its_date(self, planning: Planning) -> None:
        set_period(planning, 0, 10)
        proposed(planning, 60)

        assert upcoming(planning) == [proposed_line(60)]

    def test_every_proposed_one_shows_without_period(self, planning: Planning) -> None:
        proposed(planning, 60)

        assert upcoming(planning) == [proposed_line(60)]

    def test_confirmed_ones_up_to_the_periods_last_date(self, planning: Planning) -> None:
        set_period(planning, 5, 40)
        confirmed(planning, 40)
        confirmed(planning, 41)

        assert upcoming(planning) == [confirmed_line(40)]

    def test_a_period_ending_before_27_days_after_today_confirmed_ones_up_to_27_days(
        self, planning: Planning
    ) -> None:
        set_period(planning, 0, 10)
        confirmed(planning, 11)
        confirmed(planning, 27)
        confirmed(planning, 28)

        assert upcoming(planning) == [confirmed_line(11), confirmed_line(27)]

    def test_a_period_ending_today_confirmed_ones_up_to_27_days_after_today(
        self, planning: Planning
    ) -> None:
        set_period(planning, -5, 0)
        confirmed(planning, 1)
        confirmed(planning, 27)
        confirmed(planning, 28)

        assert upcoming(planning) == [confirmed_line(1), confirmed_line(27)]

    def test_without_period_confirmed_ones_up_to_27_days_after_today(
        self, planning: Planning
    ) -> None:
        confirmed(planning, 27)
        confirmed(planning, 28)

        assert upcoming(planning) == [confirmed_line(27)]
        assert "No upcoming registration." not in entry(planning.bruno_client).text

    def test_after_the_period_ended_confirmed_ones_up_to_27_days_after_today(
        self, planning: Planning
    ) -> None:
        set_period(planning, -10, -1)
        confirmed(planning, 27)
        confirmed(planning, 28)

        assert upcoming(planning) == [confirmed_line(27)]

    def test_with_only_later_confirmed_ones_no_upcoming_registration(
        self, planning: Planning
    ) -> None:
        confirmed(planning, 28)

        assert "No upcoming registration." in entry(planning.bruno_client).text


class TestR13R14:
    def test_reminds_when_the_user_has_no_registration_in_the_period(
        self, planning: Planning
    ) -> None:
        set_period(planning, 2, 25)

        assert reminds(planning)
        assert "No upcoming registration." not in entry(planning.bruno_client).text

    def test_reminds_alongside_registrations_outside_the_period(self, planning: Planning) -> None:
        set_period(planning, 2, 10)
        confirmed(planning, 1)
        proposed(planning, 26)

        assert reminds(planning)
        assert upcoming(planning) == [confirmed_line(1), proposed_line(26)]

    @pytest.mark.parametrize("offset", [2, 4, 6])
    @pytest.mark.parametrize("register", [confirmed, proposed])
    def test_r13_a_confirmed_or_proposed_one_within_the_period_both_dates_included(
        self, planning: Planning, offset: int, register: Callable[[Planning, int], Any]
    ) -> None:
        set_period(planning, 2, 6)
        register(planning, offset)

        assert not reminds(planning)
        assert len(bruno_lines(planning)) == 1

    def test_r13_a_cancelled_one_does_not_count(self, planning: Planning) -> None:
        set_period(planning, 2, 6)
        planning.cancel(planning.bruno_client, confirmed(planning, 3))

        assert reminds(planning)

    def test_r13_an_obsolete_one_does_not_count(self, planning: Planning) -> None:
        set_period(planning, 0, 10)
        slot = slot_on(2, planning, "14:00", "16:00")
        confirmed(planning, 2, "14:00", "16:00")
        planning.delete_slot(slot)

        assert reminds(planning)

    def test_r13_another_members_registration_does_not_count(self, planning: Planning) -> None:
        set_period(planning, 0, 10)
        planning.registered(planning.chloe_client, planning.chloe, day(2), "10:00", "13:00")

        assert reminds(planning)

    def test_r13_registrations_of_the_period_before_today_count(
        self, planning: Planning, clock: time_machine.Traveller
    ) -> None:
        set_period(planning, 1, 10)
        confirmed(planning, 1)

        clock.shift(timedelta(days=3))

        assert not reminds(planning)
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_r14_a_period_ending_today_reminds(
        self, planning: Planning, clock: time_machine.Traveller
    ) -> None:
        set_period(planning, -5, 0)

        assert reminds(planning)

    def test_r14_a_period_ended_no_longer_reminds(
        self, planning: Planning, clock: time_machine.Traveller
    ) -> None:
        set_period(planning, -5, -1)

        assert not reminds(planning)
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_r14_after_midnight_in_paris_a_period_that_ended_yesterday_no_longer_reminds(
        self, planning: Planning, clock: time_machine.Traveller
    ) -> None:
        set_period(planning, -5, 0)

        # 23:30 in UTC is already the next day in Paris.
        clock.move_to(datetime(2026, 11, 4, 23, 30, tzinfo=UTC))

        assert not reminds(planning)
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_r14_without_period_no_reminder(self, planning: Planning) -> None:
        assert not reminds(planning)
        assert "Choose your slots" not in entry(planning.bruno_client).text
        assert "No upcoming registration." in entry(planning.bruno_client).text

    def test_r14_choose_your_slots_leads_to_the_associations_schedule(
        self, planning: Planning
    ) -> None:
        set_period(planning, 2, 25)

        page = planning.bruno_client.get("/").text

        link = rf'<a[^>]*href="/association/{planning.slug}"[^>]*>\s*Choose your slots\s*</a>'
        assert re.search(link, page)

    @pytest.mark.parametrize(
        ("first", "last", "english", "french"),
        [
            (-2, 21, "2–25 Nov", "2–25 nov."),
            (-7, 21, "28 Oct – 25 Nov", "28 oct. – 25 nov."),
            (54, 65, "28 Dec 2026 – 8 Jan 2027", "28 déc. 2026 – 8 janv. 2027"),
        ],
    )
    def test_the_periods_dates(
        self, planning: Planning, first: int, last: int, english: str, french: str
    ) -> None:
        set_period(planning, first, last)

        assert f"for the planning period, {english}." in entry(planning.bruno_client).text
        planning.bruno_client.cookies.set("language", "fr")
        assert f"pour la période de planning, {french}." in entry(planning.bruno_client).text


class TestConfirm:
    def test_r7_confirms_and_answers_the_association_as_it_now_is(self, planning: Planning) -> None:
        confirmed(planning, 1)
        registration = proposed(planning, 10)

        text = shown(confirm_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC not in text
        assert listed(text) == [entry(planning.bruno_client)]
        assert bruno_lines(planning) == [confirmed_line(1), confirmed_line(10)]

    def test_r7_a_confirmed_registration_shows_the_generic_error(self, planning: Planning) -> None:
        registration = confirmed(planning, 1)

        text = shown(confirm_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == [confirmed_line(1)]

    def test_r7_a_cancelled_registration_shows_the_generic_error(self, planning: Planning) -> None:
        registration = proposed(planning, 1)
        planning.cancel(planning.bruno_client, registration)

        text = shown(confirm_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == []

    def test_r7_an_obsolete_registration_shows_the_generic_error(self, planning: Planning) -> None:
        registration = proposed(planning, 1)
        planning.add_closure(day(1), day(1))

        text = shown(confirm_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == [obsolete_line(1)]

    def test_r7_another_volunteer_does_not_confirm(self, planning: Planning) -> None:
        registration = proposed(planning, 1)

        text = shown(confirm_on_summary(planning.chloe_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == [proposed_line(1)]

    @pytest.mark.parametrize("registration_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_registration_shows_the_generic_error(
        self, planning: Planning, registration_id: str
    ) -> None:
        text = shown(confirm_on_summary(planning.bruno_client, planning.slug, registration_id))

        assert GENERIC in text

    def test_a_registration_of_another_association_shows_the_generic_error(
        self, planning: Planning
    ) -> None:
        registration = proposed(planning, 1)
        other = create_association(planning.bruno_client, "Repair Café Belleville")

        text = shown(confirm_on_summary(planning.bruno_client, other["slug"], registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == [proposed_line(1)]

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, planning: Planning, new_client: Callable[[], Any]
    ) -> None:
        registration = proposed(planning, 1)

        text = shown(confirm_on_summary(new_client(), planning.slug, registration["id"]))

        assert "window.location" in text
        assert bruno_lines(planning) == [proposed_line(1)]

    def test_a_non_member_changes_nothing(
        self, planning: Planning, new_client: Callable[[], Any]
    ) -> None:
        registration = proposed(planning, 1)

        confirm_on_summary(other_user(new_client), planning.slug, registration["id"])

        assert bruno_lines(planning) == [proposed_line(1)]


class TestOk:
    def test_r7_cancels_it_and_it_no_longer_shows(self, planning: Planning) -> None:
        confirmed(planning, 1)
        registration = confirmed(planning, 5)
        planning.add_closure(day(5), day(5))

        text = shown(ok_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC not in text
        assert listed(text) == [entry(planning.bruno_client)]
        assert bruno_lines(planning) == [confirmed_line(1)]

    def test_r7_cancels_an_obsolete_proposed_one(self, planning: Planning) -> None:
        registration = proposed(planning, 5)
        planning.add_closure(day(5), day(5))

        text = shown(ok_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC not in text
        assert bruno_lines(planning) == []

    def test_r7_a_cancelled_registration_shows_the_generic_error(self, planning: Planning) -> None:
        registration = confirmed(planning, 5)
        planning.add_closure(day(5), day(5))
        planning.cancel(planning.bruno_client, registration)

        text = shown(ok_on_summary(planning.bruno_client, planning.slug, registration["id"]))

        assert GENERIC in text

    def test_r7_another_volunteer_does_not_cancel(self, planning: Planning) -> None:
        registration = confirmed(planning, 5)
        planning.add_closure(day(5), day(5))

        text = shown(ok_on_summary(planning.chloe_client, planning.slug, registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == [obsolete_line(5)]

    @pytest.mark.parametrize("registration_id", [UNKNOWN_ID, "not-an-id"])
    def test_an_unknown_registration_shows_the_generic_error(
        self, planning: Planning, registration_id: str
    ) -> None:
        text = shown(ok_on_summary(planning.bruno_client, planning.slug, registration_id))

        assert GENERIC in text

    def test_a_registration_of_another_association_shows_the_generic_error(
        self, planning: Planning
    ) -> None:
        registration = confirmed(planning, 5)
        planning.add_closure(day(5), day(5))
        other = create_association(planning.bruno_client, "Repair Café Belleville")

        text = shown(ok_on_summary(planning.bruno_client, other["slug"], registration["id"]))

        assert GENERIC in text
        assert bruno_lines(planning) == [obsolete_line(5)]

    def test_signed_out_leads_to_sign_in_and_changes_nothing(
        self, planning: Planning, new_client: Callable[[], Any]
    ) -> None:
        registration = confirmed(planning, 5)
        planning.add_closure(day(5), day(5))

        text = shown(ok_on_summary(new_client(), planning.slug, registration["id"]))

        assert "window.location" in text
        assert bruno_lines(planning) == [obsolete_line(5)]

    def test_a_non_member_changes_nothing(
        self, planning: Planning, new_client: Callable[[], Any]
    ) -> None:
        registration = confirmed(planning, 5)
        planning.add_closure(day(5), day(5))

        ok_on_summary(other_user(new_client), planning.slug, registration["id"])

        assert bruno_lines(planning) == [obsolete_line(5)]
