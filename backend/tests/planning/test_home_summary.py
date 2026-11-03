from collections.abc import Callable, Iterator
from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest
import time_machine

from tests.planning.conftest import WEEKDAYS, Planning, create_association

# Wednesday 4 November 2026, 10:00 in Paris.
NOW = datetime(2026, 11, 4, 9, 0, tzinfo=UTC)
TODAY = date(2026, 11, 4)


def day(offset: int) -> str:
    """The date `offset` days after today."""
    return (TODAY + timedelta(days=offset)).isoformat()


@pytest.fixture
def clock() -> Iterator[time_machine.Traveller]:
    with time_machine.travel(NOW, tick=False) as traveller:
        yield traveller


@pytest.fixture
def planning(clock: time_machine.Traveller, client: Any, new_client: Callable[[], Any]) -> Planning:
    """Alice's association, open every day from 10:00 to 13:00."""
    planning = Planning(client, new_client)
    for weekday in WEEKDAYS:
        planning.add_slot(weekday, "10:00", "13:00")
    return planning


def set_period(planning: Planning, first: int, last: int) -> None:
    response = planning.alice_client.put(
        planning.path("planning-period"), json={"first": day(first), "last": day(last)}
    )
    assert response.status_code == 200, response.text


def summary(planning: Planning, as_client: Any) -> dict[str, Any]:
    """The association's entry in `GET /api/associations`."""
    response = as_client.get("/api/associations")
    assert response.status_code == 200, response.text
    entries: list[dict[str, Any]] = response.json()
    return next(entry for entry in entries if entry["id"] == planning.id)


def confirmed(planning: Planning, offset: int, start: str = "10:00", end: str = "13:00") -> Any:
    """Bruno signs up himself."""
    return planning.registered(planning.bruno_client, planning.bruno, day(offset), start, end)


def proposed(planning: Planning, offset: int) -> Any:
    """Alice proposes the occurrence to Bruno."""
    return planning.registered(planning.alice_client, planning.bruno, day(offset), "10:00", "13:00")


def upcoming_dates(planning: Planning) -> list[str]:
    return [r["date"] for r in summary(planning, planning.bruno_client)["upcoming"]]


# GET /api/associations


def test_get_api_associations_example(planning: Planning) -> None:
    set_period(planning, -2, 21)
    mine = confirmed(planning, 1)
    to_confirm = proposed(planning, 10)
    gone = confirmed(planning, 8)
    planning.add_closure(day(8), day(8))
    other = create_association(planning.bruno_client, "Repair Café Belleville")

    response = planning.bruno_client.get("/api/associations")

    assert response.status_code == 200
    assert sorted(response.json(), key=lambda a: a["name"]) == [
        {
            "id": planning.id,
            "name": "Jardin partagé des Lilas",
            "role": "volunteer",
            "upcoming": [mine, to_confirm],
            "obsolete": [gone],
            "planning_period": {"first": day(-2), "last": day(21), "registrations": 2},
        },
        {
            "id": other["id"],
            "name": "Repair Café Belleville",
            "role": "manager",
            "upcoming": [],
            "obsolete": [],
            "planning_period": None,
        },
    ]


def test_registrations_are_shown_as_post_returns_them(planning: Planning) -> None:
    registration = proposed(planning, 3)

    assert summary(planning, planning.bruno_client)["upcoming"] == [
        {
            "id": registration["id"],
            "user_id": planning.bruno["id"],
            "display_name": "Bruno",
            "status": "proposed",
            "date": day(3),
            "start": "10:00",
            "end": "13:00",
        }
    ]


def test_only_the_signed_in_users_registrations(planning: Planning) -> None:
    planning.registered(planning.chloe_client, planning.chloe, day(2), "10:00", "13:00")
    planning.registered(planning.alice_client, planning.chloe, day(3), "10:00", "13:00")
    set_period(planning, 0, 10)

    entry = summary(planning, planning.bruno_client)

    assert entry["upcoming"] == []
    assert entry["planning_period"]["registrations"] == 0


def test_r12_r13_obsolete_registrations_are_neither_upcoming_nor_counted(
    planning: Planning,
) -> None:
    set_period(planning, 0, 10)
    slot = planning.add_slot(WEEKDAYS[(TODAY + timedelta(days=2)).weekday()], "14:00", "16:00")
    confirmed(planning, 2, "14:00", "16:00")
    planning.registered(planning.alice_client, planning.bruno, day(9), "14:00", "16:00")
    assert planning.alice_client.delete(planning.path(f"slots/{slot['id']}")).status_code == 204

    entry = summary(planning, planning.bruno_client)

    assert entry["upcoming"] == []
    assert entry["planning_period"]["registrations"] == 0


def obsolete_dates(planning: Planning) -> list[str]:
    return [r["date"] for r in summary(planning, planning.bruno_client)["obsolete"]]


def test_r31_a_removed_slot_makes_its_registrations_obsolete(planning: Planning) -> None:
    slot = planning.add_slot(WEEKDAYS[(TODAY + timedelta(days=2)).weekday()], "14:00", "16:00")
    registration = confirmed(planning, 2, "14:00", "16:00")
    assert planning.alice_client.delete(planning.path(f"slots/{slot['id']}")).status_code == 204

    assert summary(planning, planning.bruno_client)["obsolete"] == [registration]


def test_r31_a_closure_makes_its_registrations_obsolete(planning: Planning) -> None:
    confirmed(planning, 3)
    proposed(planning, 4)
    confirmed(planning, 6)
    planning.add_closure(day(3), day(4))

    assert obsolete_dates(planning) == [day(3), day(4)]
    assert upcoming_dates(planning) == [day(6)]


def test_r31_an_edited_slot_makes_its_registrations_obsolete(planning: Planning) -> None:
    slot = planning.add_slot(WEEKDAYS[(TODAY + timedelta(days=2)).weekday()], "14:00", "16:00")
    confirmed(planning, 2, "14:00", "16:00")
    response = planning.alice_client.put(
        planning.path(f"slots/{slot['id']}"),
        json={"weekday": slot["weekday"], "start": "15:00", "end": "17:00"},
    )
    assert response.status_code == 200, response.text

    obsolete = summary(planning, planning.bruno_client)["obsolete"]

    assert [(r["date"], r["start"]) for r in obsolete] == [(day(2), "14:00")]


def test_r31_whatever_their_date(planning: Planning) -> None:
    set_period(planning, 0, 10)
    confirmed(planning, 60)
    planning.add_closure(day(60), day(60))

    assert obsolete_dates(planning) == [day(60)]


def test_r31_sorted_by_date_then_start(planning: Planning) -> None:
    planning.add_slot(WEEKDAYS[(TODAY + timedelta(days=2)).weekday()], "08:00", "09:00")
    confirmed(planning, 2)
    proposed(planning, 1)
    confirmed(planning, 2, "08:00", "09:00")
    planning.add_closure(day(1), day(2))

    obsolete = summary(planning, planning.bruno_client)["obsolete"]

    assert [(r["date"], r["start"]) for r in obsolete] == [
        (day(1), "10:00"),
        (day(2), "08:00"),
        (day(2), "10:00"),
    ]


def test_r31_today_is_included_and_earlier_dates_are_not(
    planning: Planning, clock: time_machine.Traveller
) -> None:
    confirmed(planning, 1)
    confirmed(planning, 2)
    planning.add_closure(day(1), day(2))

    clock.shift(timedelta(days=2))

    assert obsolete_dates(planning) == [day(2)]


def test_r31_cancelled_registrations_are_not_listed(planning: Planning) -> None:
    registration = confirmed(planning, 2)
    planning.add_closure(day(2), day(2))
    assert planning.set_status(planning.bruno_client, registration, "cancelled").status_code == 200

    assert obsolete_dates(planning) == []


def test_r31_only_the_signed_in_users_registrations(planning: Planning) -> None:
    planning.registered(planning.chloe_client, planning.chloe, day(2), "10:00", "13:00")
    planning.add_closure(day(2), day(2))

    assert obsolete_dates(planning) == []


def test_r12_cancelled_registrations_are_not_shown(planning: Planning) -> None:
    registration = confirmed(planning, 2)
    assert planning.set_status(planning.bruno_client, registration, "cancelled").status_code == 200

    assert upcoming_dates(planning) == []


def test_r12_sorted_by_date_then_start(planning: Planning) -> None:
    planning.add_slot(WEEKDAYS[(TODAY + timedelta(days=2)).weekday()], "08:00", "09:00")
    confirmed(planning, 2)
    proposed(planning, 1)
    confirmed(planning, 2, "08:00", "09:00")

    upcoming = summary(planning, planning.bruno_client)["upcoming"]

    assert [(r["date"], r["start"]) for r in upcoming] == [
        (day(1), "10:00"),
        (day(2), "08:00"),
        (day(2), "10:00"),
    ]


def test_r12_today_is_included(planning: Planning) -> None:
    confirmed(planning, 0)
    proposed(planning, 1)

    assert upcoming_dates(planning) == [day(0), day(1)]


def test_r12_registrations_before_today_are_not_shown(
    planning: Planning, clock: time_machine.Traveller
) -> None:
    confirmed(planning, 1)
    proposed(planning, 2)
    confirmed(planning, 3)

    clock.shift(timedelta(days=3))

    assert upcoming_dates(planning) == [day(3)]


def test_r12_every_proposed_one_shows_whatever_its_date(planning: Planning) -> None:
    set_period(planning, 0, 10)
    proposed(planning, 60)

    assert upcoming_dates(planning) == [day(60)]


def test_r12_every_proposed_one_shows_without_period(planning: Planning) -> None:
    proposed(planning, 60)

    assert upcoming_dates(planning) == [day(60)]


def test_r12_confirmed_ones_up_to_the_periods_last_date(planning: Planning) -> None:
    set_period(planning, 5, 40)
    confirmed(planning, 40)
    confirmed(planning, 41)

    assert upcoming_dates(planning) == [day(40)]


def test_r12_a_period_ending_before_27_days_after_today_confirmed_ones_up_to_27_days(
    planning: Planning,
) -> None:
    set_period(planning, 0, 10)
    confirmed(planning, 11)
    confirmed(planning, 27)
    confirmed(planning, 28)

    assert upcoming_dates(planning) == [day(11), day(27)]


def test_r12_a_period_ending_today_confirmed_ones_up_to_27_days_after_today(
    planning: Planning,
) -> None:
    set_period(planning, -5, 0)
    confirmed(planning, 1)
    confirmed(planning, 27)
    confirmed(planning, 28)

    assert upcoming_dates(planning) == [day(1), day(27)]


def test_r12_without_period_confirmed_ones_up_to_27_days_after_today(
    planning: Planning,
) -> None:
    confirmed(planning, 27)
    confirmed(planning, 28)

    assert upcoming_dates(planning) == [day(27)]


def test_r12_after_the_period_ended_confirmed_ones_up_to_27_days_after_today(
    planning: Planning,
) -> None:
    set_period(planning, -10, -1)
    confirmed(planning, 27)
    confirmed(planning, 28)

    assert upcoming_dates(planning) == [day(27)]


def test_r13_planning_period_is_null_without_period(planning: Planning) -> None:
    confirmed(planning, 1)

    assert summary(planning, planning.bruno_client)["planning_period"] is None


def test_r13_counts_confirmed_and_proposed_within_the_period_both_dates_included(
    planning: Planning,
) -> None:
    set_period(planning, 2, 6)
    confirmed(planning, 1)
    confirmed(planning, 2)
    proposed(planning, 4)
    confirmed(planning, 6)
    proposed(planning, 7)
    cancelled = confirmed(planning, 5)
    assert planning.set_status(planning.bruno_client, cancelled, "cancelled").status_code == 200

    assert summary(planning, planning.bruno_client)["planning_period"] == {
        "first": day(2),
        "last": day(6),
        "registrations": 3,
    }


def test_r13_counts_registrations_of_the_period_before_today(
    planning: Planning, clock: time_machine.Traveller
) -> None:
    set_period(planning, 1, 10)
    confirmed(planning, 1)
    proposed(planning, 2)

    clock.shift(timedelta(days=3))

    assert summary(planning, planning.bruno_client)["planning_period"]["registrations"] == 2
