from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, day_of_week, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def set_preference(
    planning: Planning, as_client: Any, slot: dict[str, Any], user: dict[str, Any], value: str
) -> Any:
    return as_client.put(
        planning.path(f"preferences/{slot['id']}/{user['id']}"), json={"value": value}
    )


def preferences(planning: Planning, as_client: Any) -> list[dict[str, Any]]:
    response = as_client.get(planning.path("preferences"))
    assert response.status_code == 200, response.text
    body: list[dict[str, Any]] = response.json()
    return body


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


def by_user_and_slot(body: list[dict[str, Any]]) -> set[tuple[str, str, str]]:
    return {(p["user_id"], p["slot_id"], p["value"]) for p in body}


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("GET", "preferences", None),
        ("PUT", f"preferences/{UNKNOWN_ID}/{UNKNOWN_ID}", {"value": "preferred"}),
        ("DELETE", f"preferences/{UNKNOWN_ID}/{UNKNOWN_ID}", None),
        ("GET", "registration-counts", None),
    ],
)
def test_preferences_401_when_signed_out(
    client: Any, method: str, rest: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, f"/api/associations/{UNKNOWN_ID}/{rest}", json=body)

    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("GET", "preferences", None),
        ("PUT", f"preferences/{UNKNOWN_ID}/{UNKNOWN_ID}", {"value": "preferred"}),
        ("DELETE", f"preferences/{UNKNOWN_ID}/{UNKNOWN_ID}", None),
        ("GET", "registration-counts", None),
    ],
)
def test_preferences_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any], method: str, rest: str, body: dict[str, Any] | None
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.request(method, f"/api/associations/{association['id']}/{rest}", json=body)

    assert response.status_code == 404
    assert "error" in response.json()


# Preferences


def test_put_api_preference_sets_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")

    response = set_preference(planning, planning.bruno_client, slot, planning.bruno, "possible")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": planning.bruno["id"],
        "slot_id": slot["id"],
        "value": "possible",
    }
    assert preferences(planning, planning.bruno_client) == [response.json()]


@pytest.mark.parametrize("value", ["preferred", "possible", "unavailable"])
def test_preference_values(client: Any, new_client: Callable[[], Any], value: str) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")

    response = set_preference(planning, planning.bruno_client, slot, planning.bruno, value)

    assert response.status_code == 200
    assert response.json()["value"] == value


def test_put_api_preference_replaces_the_previous_one(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_preference(planning, planning.bruno_client, slot, planning.bruno, "preferred")

    set_preference(planning, planning.bruno_client, slot, planning.bruno, "unavailable")

    assert by_user_and_slot(preferences(planning, planning.bruno_client)) == {
        (planning.bruno["id"], slot["id"], "unavailable")
    }


def test_put_api_preference_400_when_the_value_is_invalid(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")

    response = set_preference(planning, planning.bruno_client, slot, planning.bruno, "maybe")

    assert response.status_code == 400
    assert "error" in response.json()


def test_delete_api_preference_removes_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_preference(planning, planning.bruno_client, slot, planning.bruno, "preferred")

    response = planning.bruno_client.delete(
        planning.path(f"preferences/{slot['id']}/{planning.bruno['id']}")
    )

    assert response.status_code == 204
    assert preferences(planning, planning.bruno_client) == []


def test_get_api_preferences_empty_when_none_is_set(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")

    assert preferences(planning, client) == []


def test_get_api_preferences_lists_all_of_them_for_a_manager(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    thursday = planning.add_slot("thursday", "10:00", "13:00")
    saturday = planning.add_slot("saturday", "10:00", "13:00")
    set_preference(planning, client, thursday, planning.alice, "preferred")
    set_preference(planning, planning.bruno_client, thursday, planning.bruno, "unavailable")
    set_preference(planning, planning.chloe_client, saturday, planning.chloe, "possible")

    assert by_user_and_slot(preferences(planning, client)) == {
        (planning.alice["id"], thursday["id"], "preferred"),
        (planning.bruno["id"], thursday["id"], "unavailable"),
        (planning.chloe["id"], saturday["id"], "possible"),
    }


def test_get_api_preferences_lists_only_their_own_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_preference(planning, client, slot, planning.alice, "preferred")
    set_preference(planning, planning.bruno_client, slot, planning.bruno, "unavailable")
    set_preference(planning, planning.chloe_client, slot, planning.chloe, "possible")

    assert by_user_and_slot(preferences(planning, planning.bruno_client)) == {
        (planning.bruno["id"], slot["id"], "unavailable")
    }


def test_a_manager_sets_and_deletes_another_members_preference(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")

    response = set_preference(planning, client, slot, planning.bruno, "preferred")

    assert response.status_code == 200
    assert by_user_and_slot(preferences(planning, planning.bruno_client)) == {
        (planning.bruno["id"], slot["id"], "preferred")
    }

    response = client.delete(planning.path(f"preferences/{slot['id']}/{planning.bruno['id']}"))

    assert response.status_code == 204
    assert preferences(planning, planning.bruno_client) == []


def test_a_volunteer_setting_another_members_preference_403(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")

    response = set_preference(planning, planning.bruno_client, slot, planning.chloe, "preferred")

    assert response.status_code == 403
    assert "error" in response.json()
    assert preferences(planning, client) == []


def test_a_volunteer_deleting_another_members_preference_403(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_preference(planning, planning.chloe_client, slot, planning.chloe, "preferred")

    response = planning.bruno_client.delete(
        planning.path(f"preferences/{slot['id']}/{planning.chloe['id']}")
    )

    assert response.status_code == 403
    assert len(preferences(planning, client)) == 1


def test_preference_404_when_the_slot_is_not_of_this_association(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Atelier vélo")
    foreign = client.post(
        f"/api/associations/{other['id']}/slots",
        json={"weekday": "thursday", "start": "10:00", "end": "13:00"},
    ).json()

    for slot in (foreign, {"id": UNKNOWN_ID}):
        response = set_preference(planning, client, slot, planning.alice, "preferred")
        assert response.status_code == 404
        assert "error" in response.json()
        response = client.delete(planning.path(f"preferences/{slot['id']}/{planning.alice['id']}"))
        assert response.status_code == 404


def test_preference_404_when_the_user_is_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    outsider = sign_up(new_client(), "Zoé")

    for user in (outsider, {"id": UNKNOWN_ID}):
        response = set_preference(planning, client, slot, user, "preferred")
        assert response.status_code == 404
        assert "error" in response.json()


def test_deleting_a_slot_deletes_its_preferences(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    thursday = planning.add_slot("thursday", "10:00", "13:00")
    saturday = planning.add_slot("saturday", "10:00", "13:00")
    set_preference(planning, planning.bruno_client, thursday, planning.bruno, "preferred")
    set_preference(planning, planning.bruno_client, saturday, planning.bruno, "possible")

    planning.delete_slot(thursday)

    assert by_user_and_slot(preferences(planning, client)) == {
        (planning.bruno["id"], saturday["id"], "possible")
    }


def test_editing_a_slot_keeps_its_preferences(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_preference(planning, planning.bruno_client, slot, planning.bruno, "preferred")

    planning.edit_slot(slot, "friday", "14:00", "17:00")

    assert by_user_and_slot(preferences(planning, client)) == {
        (planning.bruno["id"], slot["id"], "preferred")
    }


def test_a_slot_added_again_has_no_preferences(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    set_preference(planning, planning.bruno_client, slot, planning.bruno, "preferred")
    planning.delete_slot(slot)

    planning.add_slot("thursday", "10:00", "13:00")

    assert preferences(planning, client) == []


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
