from collections.abc import Callable
from typing import Any

from tests.planning.conftest import Planning, day_of_week

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
    client.delete(planning.path(f"slots/{slot['id']}"))

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
    client.delete(planning.path(f"slots/{slot['id']}"))
    planning.add_slot("thursday", "10:00", "12:00")

    body = planning.schedule(client, thursday, thursday)

    assert body["occurrences"] == [
        {"date": thursday, "start": "10:00", "end": "12:00", "registration": None}
    ]
    assert [(r["display_name"], r["start"], r["end"]) for r in body["obsolete"]] == [
        ("Bruno", "10:00", "13:00")
    ]


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
    client.delete(planning.path(f"slots/{slot['id']}"))

    body = planning.schedule(client, thursday, thursday)

    assert body["obsolete"] == []


def test_obsolete_registrations_come_back_when_the_slot_does(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    thursday = day_of_week("thursday")
    planning.registered(planning.bruno_client, planning.bruno, thursday, "10:00", "13:00")
    client.delete(planning.path(f"slots/{slot['id']}"))
    planning.add_slot("thursday", "10:00", "13:00")

    body = planning.schedule(client, thursday, thursday)

    assert body["obsolete"] == []
    assert body["occurrences"][0]["registration"]["display_name"] == "Bruno"


def test_schedule_400_without_both_dates(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = client.get(planning.path("schedule"), params={"from": day_of_week("monday")})

    assert response.status_code == 400
    assert "error" in response.json()
