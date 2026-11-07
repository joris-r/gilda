from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
import time_machine

from tests.planning.conftest import WEEKDAYS, Planning, day_of_week

# GET /api/associations/{id}/schedule


def test_schedule_lists_the_occurrences_between_both_dates_included(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("saturday", "10:00", "13:00")
    planning.add_slot("thursday", "13:00", "16:00")
    planning.add_slot("thursday", "10:00", "13:00")
    thursday, saturday = day_of_week("thursday"), day_of_week("saturday")

    body = planning.schedule(planning.bruno_client, thursday, saturday)

    assert body["occurrences"] == [
        {"date": thursday, "start": "10:00", "end": "13:00", "registration": None},
        {"date": thursday, "start": "13:00", "end": "16:00", "registration": None},
        {"date": saturday, "start": "10:00", "end": "13:00", "registration": None},
    ]
    assert body["obsolete"] == []
    assert body["closures"] == []


def test_schedule_has_one_occurrence_per_week(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")

    body = planning.schedule(client, day_of_week("monday", 1), day_of_week("sunday", 3))

    assert [o["date"] for o in body["occurrences"]] == [
        day_of_week("thursday", 1),
        day_of_week("thursday", 2),
        day_of_week("thursday", 3),
    ]


def test_schedule_has_no_occurrence_on_a_closure_date(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    planning.add_slot("saturday", "10:00", "13:00")
    closure = planning.add_closure(
        day_of_week("saturday", 1), day_of_week("thursday", 2), "Fête du quartier"
    )

    body = planning.schedule(client, day_of_week("monday", 1), day_of_week("sunday", 2))

    assert [o["date"] for o in body["occurrences"]] == [
        day_of_week("thursday", 1),
        day_of_week("saturday", 2),
    ]
    assert body["closures"] == [closure]


def test_schedule_lists_only_the_closures_that_cover_a_date_of_the_range(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    before = planning.add_closure(day_of_week("monday", 1), day_of_week("tuesday", 2))
    inside = planning.add_closure(day_of_week("saturday", 2), day_of_week("saturday", 2))
    planning.add_closure(day_of_week("monday", 4), day_of_week("friday", 4))

    body = planning.schedule(client, day_of_week("monday", 2), day_of_week("sunday", 3))

    assert body["closures"] == [before, inside]


def test_schedule_occurrences_of_other_associations_are_not_listed(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    other = Planning(new_client(), new_client)
    other.add_slot("thursday", "10:00", "13:00")

    body = planning.schedule(client, day_of_week("monday"), day_of_week("sunday"))

    assert body["occurrences"] == []


def test_schedule_occurrence_shows_its_registration(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )

    body = planning.schedule(planning.chloe_client, thursday, thursday)

    assert body["occurrences"] == [
        {
            "date": thursday,
            "start": "10:00",
            "end": "13:00",
            "registration": {
                "id": registration["id"],
                "user_id": planning.bruno["id"],
                "display_name": "Bruno",
                "status": "confirmed",
            },
        }
    ]


def test_schedule_occurrence_shows_the_latest_cancelled_registration_when_none_other(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    for volunteer_client, volunteer in [
        (planning.bruno_client, planning.bruno),
        (planning.chloe_client, planning.chloe),
    ]:
        registration = planning.registered(volunteer_client, volunteer, thursday, "10:00", "13:00")
        assert planning.set_status(volunteer_client, registration, "cancelled").status_code == 200

    body = planning.schedule(client, thursday, thursday)

    shown = body["occurrences"][0]["registration"]
    assert (shown["display_name"], shown["status"]) == ("Chloé", "cancelled")


def test_schedule_occurrence_shows_a_new_registration_over_a_cancelled_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    cancelled = planning.registered(
        planning.chloe_client, planning.chloe, thursday, "10:00", "13:00"
    )
    planning.set_status(planning.chloe_client, cancelled, "cancelled")
    planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")

    body = planning.schedule(client, thursday, thursday)

    shown = body["occurrences"][0]["registration"]
    assert (shown["display_name"], shown["status"]) == ("Bruno", "confirmed")


# Obsolete registrations


def test_a_registration_whose_slot_was_deleted_is_obsolete(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    registration = planning.registered(client, planning.bruno, thursday, "10:00", "13:00")
    planning.delete_slot(slot)

    body = planning.schedule(planning.bruno_client, thursday, thursday)

    assert body["occurrences"] == []
    assert body["obsolete"] == [registration]


def test_a_registration_whose_slot_changed_hours_is_obsolete(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
    planning.delete_slot(slot)
    planning.add_slot("thursday", "10:00", "12:00")

    body = planning.schedule(client, thursday, thursday)

    assert body["occurrences"] == [
        {"date": thursday, "start": "10:00", "end": "12:00", "registration": None}
    ]
    assert [(r["display_name"], r["start"], r["end"]) for r in body["obsolete"]] == [
        ("Bruno", "10:00", "13:00")
    ]


def test_a_registration_whose_slot_was_edited_is_obsolete(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    registration = planning.registered(client, planning.bruno, thursday, "10:00", "13:00")

    planning.edit_slot(slot, "thursday", "14:00", "17:00")

    body = planning.schedule(client, thursday, thursday)
    assert body["occurrences"] == [
        {"date": thursday, "start": "14:00", "end": "17:00", "registration": None}
    ]
    assert body["obsolete"] == [registration]


def test_a_registration_on_a_closure_date_is_obsolete(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("saturday", "10:00", "13:00")
    saturday = day_of_week("saturday")
    planning.registered(planning.bruno_client, planning.bruno, saturday, "10:00", "13:00")
    planning.add_closure(saturday, saturday, "Fête du quartier")

    body = planning.schedule(client, saturday, saturday)

    assert body["occurrences"] == []
    assert [r["display_name"] for r in body["obsolete"]] == ["Bruno"]


def test_a_registration_on_a_date_an_edited_closure_covers_is_obsolete(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    planning.add_slot("saturday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    saturday = day_of_week("saturday")
    planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
    closure = planning.add_closure(saturday, saturday, "Fête du quartier")

    planning.edit_closure(closure, thursday, thursday, "Fête du quartier")

    body = planning.schedule(client, thursday, saturday)
    assert [(o["date"], o["registration"]) for o in body["occurrences"]] == [(saturday, None)]
    assert [(r["display_name"], r["date"]) for r in body["obsolete"]] == [("Bruno", thursday)]
    assert [(c["first"], c["last"]) for c in body["closures"]] == [(thursday, thursday)]


def test_a_cancelled_registration_is_never_obsolete(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    registration = planning.registered(
        planning.bruno_client, planning.bruno, thursday, "10:00", "13:00"
    )
    planning.set_status(planning.bruno_client, registration, "cancelled")
    planning.delete_slot(slot)

    body = planning.schedule(client, thursday, thursday)

    assert body["obsolete"] == []


def test_obsolete_registrations_come_back_when_the_slot_does(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
    planning.delete_slot(slot)
    planning.add_slot("thursday", "10:00", "13:00")

    body = planning.schedule(client, thursday, thursday)

    assert body["obsolete"] == []
    assert body["occurrences"][0]["registration"]["display_name"] == "Bruno"


@pytest.mark.parametrize("given", ["from", "to"])
def test_schedule_400_when_only_one_of_from_and_to_is_given(
    client: Any, new_client: Callable[[], Any], given: str
) -> None:
    planning = Planning(client, new_client)

    response = client.get(planning.path("schedule"), params={given: day_of_week("monday")})

    assert response.status_code == 400
    assert "error" in response.json()


def test_schedule_returns_the_range_it_was_asked_for(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    thursday, saturday = day_of_week("thursday"), day_of_week("saturday")

    body = planning.schedule(client, thursday, saturday)

    assert (body["from"], body["to"]) == (thursday, saturday)


# R32: the default range

# Monday 9 November 2026, 00:30 in Paris, still Sunday 8 November in UTC.
NOW = datetime(2026, 11, 8, 23, 30, tzinfo=UTC)


@pytest.fixture
def every_day(client: Any, new_client: Callable[[], Any]) -> Iterator[Planning]:
    """Alice's association, open every day from 10:00 to 13:00, on Monday 9 November in Paris."""
    planning = Planning(client, new_client)
    for weekday in WEEKDAYS:
        planning.add_slot(weekday, "10:00", "13:00")
    with time_machine.travel(NOW, tick=False):
        yield planning


def default_schedule(planning: Planning, as_client: Any) -> dict[str, Any]:
    response = as_client.get(planning.path("schedule"))
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def set_period(planning: Planning, first: str, last: str) -> None:
    response = planning.alice_client.put(
        planning.path("planning-period"), json={"first": first, "last": last}
    )
    assert response.status_code == 200, response.text


def test_r32_without_a_period_six_weeks_from_the_week_before_todays(
    every_day: Planning,
) -> None:
    body = default_schedule(every_day, every_day.bruno_client)

    assert (body["from"], body["to"]) == ("2026-11-02", "2026-12-13")
    dates = [o["date"] for o in body["occurrences"]]
    assert (dates[0], dates[-1], len(dates)) == ("2026-11-02", "2026-12-13", 42)


def test_r32_lists_the_closures_that_cover_a_date_of_the_default_range(
    every_day: Planning,
) -> None:
    closure = every_day.add_closure("2026-12-13", "2026-12-20", "Noël")
    every_day.add_closure("2026-12-14", "2026-12-20")

    body = default_schedule(every_day, every_day.alice_client)

    assert body["closures"] == [closure]


@pytest.mark.parametrize(
    ("last", "to"),
    [
        ("2026-12-02", "2026-12-13"),
        ("2026-12-03", "2026-12-13"),
        ("2026-12-06", "2026-12-13"),
        ("2026-12-07", "2026-12-20"),
        ("2026-12-13", "2026-12-20"),
        ("2026-12-14", "2026-12-27"),
        ("2027-01-10", "2027-01-17"),
    ],
)
def test_r32_the_range_reaches_the_end_of_the_week_after_the_periods_last_date(
    every_day: Planning, last: str, to: str
) -> None:
    set_period(every_day, "2026-11-10", last)

    body = default_schedule(every_day, every_day.bruno_client)

    assert (body["from"], body["to"]) == ("2026-11-02", to)
    assert body["occurrences"][-1]["date"] == to


def test_r32_a_past_period_leaves_six_weeks(every_day: Planning) -> None:
    set_period(every_day, "2026-10-01", "2026-10-20")

    body = default_schedule(every_day, every_day.bruno_client)

    assert (body["from"], body["to"]) == ("2026-11-02", "2026-12-13")
