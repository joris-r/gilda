from collections.abc import Callable
from typing import Any

from tests.planning.conftest import Planning, create_association, day_of_week, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def counts(planning: Planning) -> dict[str, int] | None:
    response = planning.alice_client.get(planning.path("registration-counts"))
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] | None = response.json()
    return None if body is None else {entry["user_id"]: entry["count"] for entry in body}


def set_period(planning: Planning, first: str, last: str) -> None:
    response = planning.alice_client.put(
        planning.path("planning-period"), json={"first": first, "last": last}
    )
    assert response.status_code == 200, response.text


def test_registration_counts_401_when_signed_out(client: Any) -> None:
    response = client.get(f"/api/associations/{UNKNOWN_ID}/registration-counts")

    assert response.status_code == 401
    assert "error" in response.json()


def test_registration_counts_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.get(f"/api/associations/{association['id']}/registration-counts")

    assert response.status_code == 404
    assert "error" in response.json()


# GET /api/associations/{id}/registration-counts


def test_registration_counts_null_when_there_is_no_planning_period(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)

    assert counts(planning) is None


def test_registration_counts_one_entry_per_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    set_period(planning, day_of_week("monday", 1), day_of_week("sunday", 2))

    assert counts(planning) == {
        planning.alice["id"]: 0,
        planning.bruno["id"]: 0,
        planning.chloe["id"]: 0,
    }


def test_registration_counts_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    set_period(planning, day_of_week("monday", 1), day_of_week("sunday", 2))

    response = planning.bruno_client.get(planning.path("registration-counts"))

    assert response.status_code == 403
    assert "error" in response.json()


def test_r15_counts_proposed_and_confirmed_registrations(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    planning.add_slot("saturday", "10:00", "13:00")
    set_period(planning, day_of_week("monday", 1), day_of_week("sunday", 2))
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
    )
    planning.registered(client, planning.bruno, day_of_week("saturday", 1), "10:00", "13:00")
    planning.registered(client, planning.chloe, day_of_week("thursday", 2), "10:00", "13:00")

    assert counts(planning) == {
        planning.alice["id"]: 0,
        planning.bruno["id"]: 2,
        planning.chloe["id"]: 1,
    }


def test_r15_does_not_count_cancelled_registrations(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    set_period(planning, day_of_week("monday", 1), day_of_week("sunday", 2))
    registration = planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
    )
    planning.set_status(planning.bruno_client, registration, "cancelled")

    assert counts(planning) == {
        planning.alice["id"]: 0,
        planning.bruno["id"]: 0,
        planning.chloe["id"]: 0,
    }


def test_r15_does_not_count_registrations_outside_the_planning_period(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
    )
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday", 2), "10:00", "13:00"
    )
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday", 3), "10:00", "13:00"
    )
    set_period(planning, day_of_week("thursday", 2), day_of_week("thursday", 2))

    assert counts(planning) == {
        planning.alice["id"]: 0,
        planning.bruno["id"]: 1,
        planning.chloe["id"]: 0,
    }


def test_r15_does_not_count_obsolete_registrations(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_period(planning, day_of_week("monday", 1), day_of_week("sunday", 2))
    planning.registered(
        planning.bruno_client, planning.bruno, day_of_week("thursday", 1), "10:00", "13:00"
    )
    planning.delete_slot(slot)

    assert counts(planning) == {
        planning.alice["id"]: 0,
        planning.bruno["id"]: 0,
        planning.chloe["id"]: 0,
    }
