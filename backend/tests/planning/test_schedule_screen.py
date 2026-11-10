# ruff: noqa: RUF001  (lines are written with a middle dot and dates with an en dash)
import html
import re
from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime
from typing import Any
from zoneinfo import ZoneInfo

import pytest
import time_machine

from tests.core.conftest import delete_association, unique_slug
from tests.planning.conftest import (
    GENERIC,
    WEEKDAYS,
    Planning,
    add_closure_on_screen,
    add_member,
    day_in,
    day_label,
    day_of_week,
    day_shown,
    headings_of,
    more_weeks,
    part,
    schedule_entries,
    schedule_page,
    schedule_shown,
    set_period,
    shown,
    sign_up,
    text_of,
    unique_email,
    without_dialogs,
)

NAME = "Jardin partagé des Lilas"
UNKNOWN = "This association does not exist or you are not a member."
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
EMPTY = "No openings in these weeks."

# Monday 9 November 2026, 00:30 in Paris, still Sunday 8 November in UTC.
NOW = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)
WEEKS_OPENED = ["Week 45", "Week 46", "Week 47", "Week 48", "Week 49", "Week 50"]


def other_user(new_client: Callable[[], Any]) -> Any:
    """Zoé, signed in on her own client, who is not a member."""
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))
    return other


def collapsed(fragment: str) -> str:
    return " ".join(text_of(fragment).split())


def items(day: str) -> list[str]:
    """The occurrences and obsolete registrations a day shows, sorted, as their placement on
    the screen, not their order, follows their times."""
    return sorted(re.findall(r"\[[^\]]*\]", day))


def today_in_paris() -> date:
    return datetime.now(ZoneInfo("Europe/Paris")).date()


def thursdays(first: int, last: int) -> list[str]:
    """The Thursdays of the weeks `first` to `last` weeks after the current one."""
    return [day_of_week("thursday", n) for n in range(first, last + 1)]


def period_set(planning: Planning, first: str, last: str) -> None:
    text = shown(set_period(planning.alice_client, planning.slug, first, last))
    assert GENERIC not in text, text


def cancelled(planning: Planning, as_client: Any, registration: dict[str, Any]) -> None:
    planning.cancel(as_client, registration)


@pytest.fixture
def thursdays_on_now(client: Any, new_client: Callable[[], Any]) -> Iterator[Planning]:
    """Alice's association, open on Thursdays from 10:00 to 13:00, on Monday 9 November in
    Paris."""
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    with time_machine.travel(NOW, tick=False):
        yield planning


class TestScheduleHeader:
    # /core/ui/header/location
    def test_shows_the_association_name_alone(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        header = collapsed(part(schedule_page(planning.bruno_client, planning.slug), "header"))

        assert NAME in header
        assert "Bruno" in header
        assert "›" not in header

    # /core/ui/header/title
    def test_the_location_stands_for_the_title(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        main = text_of(without_dialogs(part(schedule_page(client, planning.slug), "main")))

        assert NAME not in main

    # /planning/ui/schedule/links
    @pytest.mark.parametrize(
        ("screen", "rest"),
        [
            ("My availability", "availability"),
            ("Members", "members"),
            ("Schedule settings", "settings"),
        ],
    )
    def test_my_availability_members_and_schedule_settings_lead_to_those_screens(
        self, client: Any, new_client: Callable[[], Any], screen: str, rest: str
    ) -> None:
        planning = Planning(client, new_client)

        for as_client in (planning.alice_client, planning.bruno_client):
            page = schedule_page(as_client, planning.slug)
            assert re.search(
                rf'<a[^>]*href="/association/{planning.slug}/{rest}"[^>]*>\s*{screen}\s*</a>', page
            )

    # /planning/ui/schedule/links
    # /planning/ui/schedule-settings/french
    # /planning/ui/my-availability/french
    # /core/ui/header/language
    def test_the_links_follow_the_language(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        page = html.unescape(schedule_page(client, planning.slug))

        for screen, rest in [
            ("Mes disponibilités", "availability"),
            ("Membres", "members"),
            ("Réglages du planning", "settings"),
        ]:
            assert re.search(
                rf'<a[^>]*href="/association/{planning.slug}/{rest}"[^>]*>\s*{screen}\s*</a>', page
            )

    # /core/ui/access/signed-out
    def test_signed_out_shows_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        response = new_client().get(f"/association/{planning.slug}")

        assert response.status_code == 200
        assert 'type="password"' in response.text
        assert NAME not in response.text


class TestUnknownAssociation:
    # /core/ui/unknown-association/shown
    def test_an_unknown_slug_says_so_with_a_way_to_my_associations(self, client: Any) -> None:
        sign_up(client, "Alice")

        response = client.get(f"/association/{unique_slug()}")

        assert response.status_code == 200
        main = html.unescape(part(response.text, "main"))
        assert UNKNOWN in main
        assert re.search(r'<a[^>]*href="/"[^>]*>\s*My associations\s*</a>', main)
        assert "Page not found" not in response.text

    # /core/ui/unknown-association/shown
    def test_an_association_of_others_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        response = other_user(new_client).get(f"/association/{planning.slug}")

        assert response.status_code == 200
        assert UNKNOWN in html.unescape(response.text)
        assert NAME not in response.text
        assert "Week" not in response.text

    # /core/ui/unknown-association/shown
    def test_a_deleted_association_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        shown(delete_association(client, planning.slug))

        response = planning.bruno_client.get(f"/association/{planning.slug}")

        assert response.status_code == 200
        assert UNKNOWN in html.unescape(response.text)

    # /core/ui/unknown-association/shown
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any) -> None:
        sign_up(client, "Alice")
        client.cookies.set("language", "fr")

        page = html.unescape(client.get(f"/association/{unique_slug()}").text)

        assert "Cette association n'existe pas ou vous n'en êtes pas membre." in page


class TestDefaultWeeks:
    # /planning/operations/get-schedule/default
    # /planning/ui/schedule/weeks
    def test_without_a_period_six_weeks_from_the_week_before_todays(
        self, thursdays_on_now: Planning
    ) -> None:
        entries = schedule_shown(thursdays_on_now.bruno_client, thursdays_on_now.slug)

        assert headings_of(entries) == WEEKS_OPENED
        weeks = [entry for entry in entries if isinstance(entry, tuple)]
        assert weeks[0] == ("Week 45", ["Thu 5 Nov []"])
        assert weeks[-1] == ("Week 50", ["Thu 10 Dec []"])

    # /planning/operations/get-schedule/default
    # /planning/ui/schedule/weeks
    def test_each_week_shows_every_occurrence_of_its_days(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        for weekday in WEEKDAYS:
            planning.add_slot(weekday, "10:00", "13:00")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        weeks = [entry for entry in entries if isinstance(entry, tuple)]
        assert weeks[1] == (
            "Week 46",
            [
                "Mon 9 Nov []",
                "Tue 10 Nov []",
                "Wed 11 Nov []",
                "Thu 12 Nov []",
                "Fri 13 Nov []",
                "Sat 14 Nov []",
                "Sun 15 Nov []",
            ],
        )
        assert [len(days) for _, days in weeks] == [7] * 6

    # /planning/operations/get-schedule/default
    # /planning/ui/schedule/weeks
    @pytest.mark.parametrize(
        ("last", "weeks"),
        [
            ("2026-12-02", WEEKS_OPENED),
            ("2026-12-06", WEEKS_OPENED),
            ("2026-12-07", [*WEEKS_OPENED, "Week 51"]),
            ("2026-12-13", [*WEEKS_OPENED, "Week 51"]),
            ("2026-12-14", [*WEEKS_OPENED, "Week 51", "Week 52"]),
            (
                "2027-01-10",
                [*WEEKS_OPENED, "Week 51", "Week 52", "Week 53", "Week 1", "Week 2"],
            ),
        ],
    )
    def test_reaches_the_end_of_the_week_after_the_periods_last_date(
        self, client: Any, new_client: Callable[[], Any], last: str, weeks: list[str]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        period_set(planning, "2026-11-10", last)

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        assert headings_of(entries) == weeks

    # /planning/operations/get-schedule/default
    def test_a_past_period_leaves_six_weeks(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        period_set(planning, "2026-10-01", "2026-10-20")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        assert headings_of(entries) == WEEKS_OPENED

    # /planning/operations/get-schedule/default
    def test_a_manager_sees_the_same_weeks(self, thursdays_on_now: Planning) -> None:
        manager = schedule_shown(thursdays_on_now.alice_client, thursdays_on_now.slug)
        volunteer = schedule_shown(thursdays_on_now.bruno_client, thursdays_on_now.slug)

        assert manager == volunteer


class TestToday:
    # /planning/model/time-zone/today
    # /planning/ui/schedule/today
    # /planning/operations/get-schedule/default
    # /core/model/association/timezone
    @pytest.mark.parametrize(
        ("now", "line", "first_week"),
        [
            (NOW, "Today · Monday 9 November 2026", "Week 45"),
            (
                datetime(2026, 11, 8, 22, 30, tzinfo=UTC),
                "Today · Sunday 8 November 2026",
                "Week 44",
            ),
            (
                datetime(2026, 7, 5, 22, 30, tzinfo=UTC),
                "Today · Monday 6 July 2026",
                "Week 27",
            ),
        ],
        ids=["after_midnight_in_paris", "before_midnight_in_paris", "summer_time"],
    )
    def test_today_is_the_date_in_the_associations_timezone(
        self,
        client: Any,
        new_client: Callable[[], Any],
        now: datetime,
        line: str,
        first_week: str,
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        with time_machine.travel(now, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        assert line in entries
        assert headings_of(entries)[0] == first_week


class TestTodayAndPeriodLines:
    # /planning/ui/schedule/today
    def test_the_today_line_separates_the_past_weeks_from_the_current_week(
        self, thursdays_on_now: Planning
    ) -> None:
        entries = schedule_shown(thursdays_on_now.bruno_client, thursdays_on_now.slug)

        assert [e if isinstance(e, str) else e[0] for e in entries] == [
            "Week 45",
            "Today · Monday 9 November 2026",
            *WEEKS_OPENED[1:],
        ]

    # /planning/ui/schedule/today
    def test_the_today_line_shows_today_without_time_travel(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        today = today_in_paris()
        months = [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ]
        line = (
            f"Today · {WEEKDAYS[today.weekday()].title()} {today.day} "
            f"{months[today.month - 1]} {today.year}"
        )

        entries = schedule_shown(planning.bruno_client, planning.slug)

        assert entries.index(line) == 1
        assert headings_of(entries)[1] == f"Week {today.isocalendar().week}"

    # /planning/ui/schedule/period-lines
    def test_the_period_lines_sit_before_the_week_of_its_first_date_and_after_that_of_its_last(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        period_set(planning, "2026-11-17", "2026-11-25")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        assert [e if isinstance(e, str) else e[0] for e in entries] == [
            "Week 45",
            "Today · Monday 9 November 2026",
            "Week 46",
            "Planning start · Tuesday 17 November 2026",
            "Week 47",
            "Week 48",
            "Planning end · Wednesday 25 November 2026",
            "Week 49",
            "Week 50",
        ]

    # /planning/ui/schedule/period-lines
    def test_the_today_line_comes_first_when_both_fall_at_the_same_place(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        period_set(planning, "2026-11-10", "2026-11-10")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        assert [e if isinstance(e, str) else e[0] for e in entries] == [
            "Week 45",
            "Today · Monday 9 November 2026",
            "Planning start · Tuesday 10 November 2026",
            "Week 46",
            "Planning end · Tuesday 10 November 2026",
            *WEEKS_OPENED[2:],
        ]

    # /planning/ui/schedule/period-lines
    def test_a_period_that_started_before_the_shown_weeks_shows_only_its_last_line(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        period_set(planning, "2026-10-01", "2026-11-25")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        lines = [entry for entry in entries if isinstance(entry, str)]
        assert lines == [
            "Today · Monday 9 November 2026",
            "Planning end · Wednesday 25 November 2026",
        ]

    # /planning/ui/schedule/period-lines
    def test_without_a_period_or_with_a_past_one_shows_no_period_line(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        with time_machine.travel(NOW, tick=False):
            without = schedule_shown(planning.bruno_client, planning.slug)
        period_set(planning, "2026-10-01", "2026-10-20")

        with time_machine.travel(NOW, tick=False):
            past = schedule_shown(planning.bruno_client, planning.slug)

        for entries in (without, past):
            assert [e for e in entries if isinstance(e, str)] == ["Today · Monday 9 November 2026"]

    # /planning/ui/schedule/today
    # /planning/ui/schedule/period-lines
    # /core/ui/header/language
    def test_follow_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        period_set(planning, "2026-11-17", "2026-11-25")
        planning.bruno_client.cookies.set("language", "fr")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        assert [e if isinstance(e, str) else e[0] for e in entries][:5] == [
            "Semaine 45",
            "Aujourd'hui · lundi 9 novembre 2026",
            "Semaine 46",
            "Début de planification · mardi 17 novembre 2026",
            "Semaine 47",
        ]
        assert "Fin de planification · mercredi 25 novembre 2026" in entries


class TestColumns:
    def test_one_column_per_weekday_on_which_an_occurrence_falls(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        planning.add_slot("thursday", "14:00", "17:00")
        planning.add_slot("thursday", "10:00", "13:00")

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        weeks = [entry for entry in entries if isinstance(entry, tuple)]
        assert weeks[1] == ("Week 46", ["Thu 12 Nov [] []", "Sat 14 Nov []"])

    # /planning/ui/schedule/closed
    def test_a_weekday_closed_in_one_week_keeps_its_column(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        shown(add_closure_on_screen(client, planning.slug, "2026-11-14", "2026-11-14", "Fête"))

        with time_machine.travel(NOW, tick=False):
            entries = schedule_shown(planning.bruno_client, planning.slug)

        weeks = [entry for entry in entries if isinstance(entry, tuple)]
        assert weeks[1] == ("Week 46", ["Thu 12 Nov []", "Sat 14 Nov Closed Fête"])

    # /core/ui/header/language
    def test_day_labels_follow_the_language(self, thursdays_on_now: Planning) -> None:
        thursdays_on_now.bruno_client.cookies.set("language", "fr")

        entries = schedule_shown(thursdays_on_now.bruno_client, thursdays_on_now.slug)

        weeks = [entry for entry in entries if isinstance(entry, tuple)]
        assert weeks[1] == ("Semaine 46", ["jeu. 12 nov. []"])


class TestTimeScale:
    def test_runs_from_the_earliest_start_to_the_latest_end_rounded_to_whole_hours(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:30", "13:00")
        planning.add_slot("saturday", "14:00", "16:15")

        page = schedule_page(planning.bruno_client, planning.slug)

        weeks = re.findall(
            r'<section[^>]*class="week[^"]*"[^>]*>.*?</section>',
            without_dialogs(part(page, "main")),
            re.DOTALL,
        )
        assert len(weeks) == 6
        for week in weeks:
            before_days = re.split(r'(?=<[a-z]+[^>]*\srole="group")', week)[0]
            ticks = re.findall(r"\b\d{1,2}h\b", text_of(before_days))
            assert ticks == [f"{hour}h" for hour in range(10, 18)], week


class TestOccurrences:
    # /planning/ui/schedule/occurrence
    def test_without_a_registration_an_occurrence_is_empty(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        assert day_shown(planning.bruno_client, planning.slug, day_of_week("thursday")) == "[]"

    # /planning/ui/schedule/occurrence
    def test_shows_its_registrations_display_name_and_no_times(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        assert day_shown(planning.chloe_client, planning.slug, thursday) == "[Bruno]"

    # /planning/ui/schedule/occurrence
    def test_a_proposed_registration_shows_a_question_mark(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(client, planning.bruno, thursday, "10:00", "13:00")

        assert day_shown(planning.chloe_client, planning.slug, thursday) == "[Bruno ?]"

    # /planning/ui/schedule/occurrence
    def test_a_cancelled_registration_shows_its_name_struck(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        registration = planning.registered(
            planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
        )
        cancelled(planning, planning.bruno_client, registration)

        assert day_shown(planning.chloe_client, planning.slug, thursday) == "[~~Bruno~~]"

    # /planning/ui/schedule/occurrence
    # /planning/operations/get-schedule/registration
    def test_shows_the_latest_cancelled_registration_when_none_other(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        for volunteer_client, volunteer in [
            (planning.bruno_client, planning.bruno),
            (planning.chloe_client, planning.chloe),
        ]:
            registration = planning.registered(
                volunteer_client, volunteer, thursday, "10:00", "13:00"
            )
            cancelled(planning, volunteer_client, registration)

        assert day_shown(client, planning.slug, thursday) == "[~~Chloé~~]"

    # /planning/ui/schedule/occurrence
    # /planning/operations/get-schedule/registration
    def test_shows_a_new_registration_over_a_cancelled_one(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        registration = planning.registered(
            planning.chloe_client, planning.chloe, thursday, "10:00", "13:00"
        )
        cancelled(planning, planning.chloe_client, registration)
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        assert day_shown(client, planning.slug, thursday) == "[Bruno]"

    # /planning/ui/schedule/occurrence
    # /planning/model/occurrence/identity
    def test_each_occurrence_of_a_day_shows_its_own_registration(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "14:00", "17:00")
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "14:00", "17:00")

        assert items(day_shown(client, planning.slug, thursday)) == ["[Bruno]", "[]"]

    # /planning/operations/get-schedule/order
    def test_occurrences_and_obsolete_registrations_come_by_date_then_start(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "09:00", "10:00")
        planning.add_slot("thursday", "14:00", "17:00")
        obsolete = planning.add_slot("thursday", "11:00", "12:00")
        planning.add_slot("thursday", "10:00", "13:00")
        thursday, saturday = day_of_week("thursday"), day_of_week("saturday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "11:00", "12:00")
        planning.delete_slot(obsolete)

        main = without_dialogs(part(schedule_page(client, planning.slug), "main"))
        groups = re.split(r'(?=<[a-z]+[^>]*\srole="group")', main)[1:]
        shown_in_order = [
            html.unescape(label)
            for group in groups
            if re.search(rf'aria-label="({day_label(thursday)}|{day_label(saturday)})"', group)
            for label in re.findall(r'<li[^>]*class="occ[^"]*"[^>]*aria-label="([^"]*)"', group)
        ]

        assert shown_in_order == ["10–13", "11–12 Bruno obsolete", "14–17", "9–10"]

    # /planning/ui/schedule/occurrence
    def test_one_occurrence_per_week(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        days = thursdays(1, 3)
        for day, (volunteer_client, volunteer) in zip(
            days,
            [
                (planning.bruno_client, planning.bruno),
                (planning.chloe_client, planning.chloe),
                (planning.bruno_client, planning.bruno),
            ],
            strict=True,
        ):
            planning.registered(volunteer_client, volunteer, day, "10:00", "13:00")

        entries = schedule_shown(client, planning.slug)

        assert [day_in(entries, day) for day in days] == ["[Bruno]", "[Chloé]", "[Bruno]"]

    # /planning/ui/schedule/occurrence
    def test_shows_only_the_occurrences_of_its_association(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        other = Planning(new_client(), new_client)
        other.add_slot("saturday", "10:00", "13:00")
        other.registered(other.bruno_client, other.bruno, day_of_week("saturday"), "10:00", "13:00")

        entries = schedule_shown(client, planning.slug)

        weeks = [entry for entry in entries if isinstance(entry, tuple)]
        assert all(len(days) == 1 for _, days in weeks)
        assert day_label(day_of_week("saturday")) not in str(entries)

    def test_escapes_the_display_name(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        volunteer = new_client()
        email = unique_email("Zoe")
        user = sign_up(volunteer, "<b>Zoé</b>", email)
        add_member(client, planning.slug, "<b>Zoé</b>", email)
        planning.registered(volunteer, user, day_of_week("thursday"), "10:00", "13:00")

        page = schedule_page(client, planning.slug)

        assert "<b>Zoé</b>" not in page
        assert "&lt;b&gt;Zoé&lt;/b&gt;" in page


class TestNoOpenings:
    # /planning/ui/schedule/empty
    def test_without_an_occurrence_says_so(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)

        main = collapsed(without_dialogs(part(schedule_page(client, planning.slug), "main")))

        assert EMPTY in main

    # /planning/ui/schedule/empty
    def test_with_an_occurrence_says_nothing_of_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        assert EMPTY not in schedule_page(client, planning.slug)

    # /planning/ui/schedule/empty
    def test_with_only_an_obsolete_registration_says_nothing_of_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        planning.registered(client, planning.bruno, day_of_week("thursday"), "10:00", "13:00")
        planning.delete_slot(slot)

        assert EMPTY not in schedule_page(client, planning.slug)

    # /planning/ui/schedule/empty
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        client.cookies.set("language", "fr")

        main = collapsed(without_dialogs(part(schedule_page(client, planning.slug), "main")))

        assert "Aucune ouverture sur ces semaines." in main


class TestClosures:
    # /planning/ui/schedule/closed
    def test_a_day_covered_by_a_closure_shows_closed_and_its_label(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        saturday = day_of_week("saturday")
        planning.add_closure(saturday, saturday, "Fête du quartier")

        entries = schedule_shown(planning.bruno_client, planning.slug)

        assert day_in(entries, saturday) == "Closed Fête du quartier"
        assert day_in(entries, day_of_week("saturday", 2)) == "[]"

    # /planning/ui/schedule/closed
    # /planning/operations/add-closure/no-label
    def test_a_closure_without_a_label_shows_closed(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.add_closure(thursday, thursday)

        assert day_shown(planning.bruno_client, planning.slug, thursday) == "Closed"

    # /planning/ui/schedule/closed
    def test_covers_each_day_from_its_first_to_its_last(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        planning.add_closure(day_of_week("saturday", 1), day_of_week("thursday", 2), "Fête")

        entries = schedule_shown(client, planning.slug)

        assert [
            day_in(entries, day)
            for day in [
                day_of_week("thursday", 1),
                day_of_week("saturday", 1),
                day_of_week("thursday", 2),
                day_of_week("saturday", 2),
            ]
        ] == ["[]", "Closed Fête", "Closed Fête", "[]"]

    # /planning/ui/schedule/closed
    # /planning/operations/get-schedule/closures
    def test_a_closure_that_started_before_the_shown_weeks_shows_on_its_shown_days(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_closure(day_of_week("monday", -4), day_of_week("sunday", -1), "Travaux")

        entries = schedule_shown(client, planning.slug)

        assert day_in(entries, day_of_week("thursday", -1)) == "Closed Travaux"
        assert day_in(entries, day_of_week("thursday", 0)) == "[]"

    # /planning/ui/schedule/closed
    # /planning/ui/schedule/obsolete
    # /planning/model/registration/obsolete
    def test_the_closure_hides_the_registration_held_on_it(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("saturday", "10:00", "13:00")
        saturday = day_of_week("saturday")
        planning.registered(planning.bruno_client, planning.bruno, saturday, "10:00", "13:00")
        planning.add_closure(saturday, saturday, "Fête du quartier")

        assert day_shown(client, planning.slug, saturday) == (
            "Closed Fête du quartier [Bruno obsolete]"
        )

    # /planning/ui/schedule/closed
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.add_closure(thursday, thursday, "Fête")
        client.cookies.set("language", "fr")

        entries = schedule_shown(client, planning.slug)

        days = [text for entry in entries if isinstance(entry, tuple) for text in entry[1]]
        assert any(text.endswith(" Fermé Fête") for text in days), days


class TestObsoleteRegistrations:
    # /planning/ui/schedule/obsolete
    # /planning/model/registration/obsolete
    def test_a_registration_whose_slot_was_deleted_shows_on_its_day_marked_obsolete(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(client, planning.bruno, thursday, "10:00", "13:00")
        planning.delete_slot(slot)

        assert day_shown(planning.bruno_client, planning.slug, thursday) == "[Bruno ? obsolete]"

    # /planning/ui/schedule/obsolete
    # /planning/model/registration/obsolete
    def test_a_registration_whose_slot_changed_hours_is_obsolete(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
        planning.delete_slot(slot)
        planning.add_slot("thursday", "10:00", "12:00")

        assert items(day_shown(client, planning.slug, thursday)) == ["[Bruno obsolete]", "[]"]

    # /planning/ui/schedule/obsolete
    # /planning/model/registration/obsolete
    def test_a_registration_whose_slot_was_edited_is_obsolete(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        planning.edit_slot(slot, "thursday", "14:00", "17:00")

        assert items(day_shown(client, planning.slug, thursday)) == ["[Bruno obsolete]", "[]"]

    # /planning/ui/schedule/obsolete
    # /planning/model/registration/obsolete
    def test_a_registration_on_a_date_an_edited_closure_covers_is_obsolete(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        saturday = day_of_week("saturday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
        closure = planning.add_closure(saturday, saturday, "Fête du quartier")

        planning.edit_closure(closure, thursday, thursday, "Fête du quartier")

        entries = schedule_shown(client, planning.slug)
        assert day_in(entries, thursday) == "Closed Fête du quartier [Bruno obsolete]"
        assert day_in(entries, saturday) == "[]"

    # /planning/model/registration/obsolete
    def test_a_cancelled_registration_is_never_obsolete(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        registration = planning.registered(
            planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
        )
        cancelled(planning, planning.bruno_client, registration)
        planning.delete_slot(slot)

        assert "Bruno" not in str(schedule_shown(client, planning.slug))

    # /planning/model/registration/obsolete
    # /planning/ui/schedule/occurrence
    # /planning/model/occurrence/identity
    def test_comes_back_as_the_occurrences_registration_when_the_slot_does(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
        planning.delete_slot(slot)
        planning.add_slot("thursday", "10:00", "13:00")

        assert day_shown(client, planning.slug, thursday) == "[Bruno]"

    # /planning/ui/schedule/obsolete
    # /core/ui/header/language
    def test_follows_the_language(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        slot = planning.add_slot("thursday", "10:00", "13:00")
        planning.registered(client, planning.bruno, day_of_week("thursday"), "10:00", "13:00")
        planning.delete_slot(slot)
        client.cookies.set("language", "fr")

        assert "[Bruno ? obsolète]" in str(schedule_shown(client, planning.slug))


class TestMoreWeeks:
    # /planning/ui/schedule/weeks
    def test_is_at_the_end(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")

        main = without_dialogs(part(schedule_page(planning.bruno_client, planning.slug), "main"))

        button = re.search(r"<button[^>]*>\s*More weeks\s*</button>", main)
        assert button
        assert main.rfind("</section>") < button.start()

    # /planning/ui/schedule/more
    def test_adds_the_four_weeks_that_follow(self, thursdays_on_now: Planning) -> None:
        planning = thursdays_on_now

        text = shown(more_weeks(planning.bruno_client, planning.slug, "2026-11-02", "2026-12-13"))

        entries = schedule_entries(text)
        assert headings_of(entries) == [
            *WEEKS_OPENED,
            "Week 51",
            "Week 52",
            "Week 53",
            "Week 1",
        ]
        assert "Today · Monday 9 November 2026" in entries
        assert re.search(r"<button[^>]*>\s*More weeks\s*</button>", text)

    # /planning/ui/schedule/more
    def test_adds_four_more_each_time(self, thursdays_on_now: Planning) -> None:
        planning = thursdays_on_now

        text = shown(more_weeks(planning.bruno_client, planning.slug, "2026-11-02", "2027-01-10"))

        assert headings_of(schedule_entries(text))[-5:] == [
            "Week 1",
            "Week 2",
            "Week 3",
            "Week 4",
            "Week 5",
        ]
        assert len(headings_of(schedule_entries(text))) == 14

    # /planning/ui/schedule/more
    def test_the_weeks_added_show_their_occurrences_closures_and_period_line(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        planning.add_slot("saturday", "10:00", "13:00")
        late_thursday, late_saturday = day_of_week("thursday", 7), day_of_week("saturday", 7)
        planning.registered(planning.bruno_client, planning.bruno, late_thursday, "10:00", "13:00")
        planning.add_closure(late_saturday, late_saturday, "Fête")

        text = shown(
            more_weeks(
                planning.chloe_client,
                planning.slug,
                day_of_week("monday", -1),
                day_of_week("sunday", 4),
            )
        )

        entries = schedule_entries(text)
        assert len(headings_of(entries)) == 10
        assert day_in(entries, late_thursday) == "[Bruno]"
        assert day_in(entries, late_saturday) == "Closed Fête"

    # /planning/ui/schedule/more
    # /core/ui/header/language
    def test_follows_the_language(self, thursdays_on_now: Planning) -> None:
        planning = thursdays_on_now
        planning.bruno_client.cookies.set("language", "fr")

        text = shown(more_weeks(planning.bruno_client, planning.slug, "2026-11-02", "2026-12-13"))

        assert headings_of(schedule_entries(text))[-1] == "Semaine 1"
        assert "Plus de semaines" in text

    # /ui/errors/generic
    @pytest.mark.parametrize(
        "body",
        [
            {"to": "2026-12-13"},
            {"from": "2026-11-02"},
            {"from": "2026-11-02", "to": "13/12/2026"},
            {"from": "", "to": "2026-12-13"},
            {"from": "2026-12-13", "to": "2026-11-02"},
        ],
    )
    def test_a_missing_or_invalid_range_shows_the_generic_error(
        self, client: Any, new_client: Callable[[], Any], body: dict[str, Any]
    ) -> None:
        planning = Planning(client, new_client)

        text = shown(client.post(f"/association/{planning.slug}/weeks", json=body))

        assert GENERIC in text
        assert "Week" not in text

    # /planning/operations/general/member
    def test_a_non_member_sees_none_of_the_weeks(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        planning.add_slot("thursday", "10:00", "13:00")
        thursday = day_of_week("thursday")
        planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

        response = more_weeks(
            other_user(new_client), planning.slug, day_of_week("monday"), day_of_week("sunday")
        )

        assert "Bruno" not in response.text
        assert "Week" not in response.text

    # /core/ui/access/action
    def test_signed_out_leads_to_sign_in(self, client: Any, new_client: Callable[[], Any]) -> None:
        planning = Planning(client, new_client)

        text = shown(
            more_weeks(new_client(), planning.slug, day_of_week("monday"), day_of_week("sunday"))
        )

        assert "window.location" in text
        assert "Week" not in text
