import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, settings_lines, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


# Signed-in member required


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("POST", "slots", {"weekday": "thursday", "start": "10:00", "end": "13:00"}),
        ("POST", "closures", {"first": "2026-12-24", "last": "2026-12-26", "label": None}),
        # @dev43:unsure
        ("GET", "schedule?from=2026-11-02&to=2026-11-08", None),
        (
            "POST",
            "registrations",
            {"user_id": UNKNOWN_ID, "date": "2026-11-05", "start": "10:00", "end": "13:00"},
        ),
        ("PATCH", f"registrations/{UNKNOWN_ID}", {"status": "confirmed"}),
    ],
)
def test_planning_401_when_signed_out(
    client: Any, method: str, rest: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, f"/api/associations/{UNKNOWN_ID}/{rest}", json=body)

    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("POST", "slots", {"weekday": "thursday", "start": "10:00", "end": "13:00"}),
        ("POST", "closures", {"first": "2026-12-24", "last": "2026-12-26", "label": None}),
        # @dev43:unsure
        ("GET", "schedule?from=2026-11-02&to=2026-11-08", None),
    ],
)
def test_planning_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any], method: str, rest: str, body: dict[str, Any] | None
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.request(method, f"/api/associations/{association['id']}/{rest}", json=body)

    assert response.status_code == 404
    assert "error" in response.json()


# Slots


def test_post_api_slots_creates_a_slot(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = client.post(
        planning.path("slots"), json={"weekday": "saturday", "start": "10:00", "end": "13:00"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "weekday": "saturday", "start": "10:00", "end": "13:00"}
    uuid.UUID(body["id"])


def test_slots_are_kept_to_the_minute(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    slot = planning.add_slot("friday", "18:30", "20:15")

    assert (slot["start"], slot["end"]) == ("18:30", "20:15")


def test_post_api_slots_409_when_the_association_already_has_that_slot(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")

    response = client.post(
        planning.path("slots"), json={"weekday": "thursday", "start": "10:00", "end": "13:00"}
    )

    assert response.status_code == 409
    assert "error" in response.json()


def test_the_same_slot_in_two_associations(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("thursday", "10:00", "13:00")
    other = create_association(client, "Repair Café Belleville")

    response = client.post(
        f"/api/associations/{other['id']}/slots",
        json={"weekday": "thursday", "start": "10:00", "end": "13:00"},
    )

    assert response.status_code == 201


@pytest.mark.parametrize(
    "body",
    [
        {"start": "10:00", "end": "13:00"},
        {"weekday": "someday", "start": "10:00", "end": "13:00"},
        {"weekday": "thursday", "start": "13:00", "end": "10:00"},
        {"weekday": "thursday", "start": "10:00", "end": "10:00"},
        {"weekday": "thursday", "start": "10h", "end": "13:00"},
        {"weekday": "thursday", "start": "10:00"},
    ],
)
def test_post_api_slots_400_when_a_field_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, str]
) -> None:
    planning = Planning(client, new_client)

    response = client.post(planning.path("slots"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


def test_post_api_slots_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    created = planning.bruno_client.post(
        planning.path("slots"), json={"weekday": "saturday", "start": "10:00", "end": "13:00"}
    )

    assert created.status_code == 403
    # Alice can still add it: Bruno's request created nothing.
    planning.add_slot("saturday", "10:00", "13:00")


# Closures


def test_post_api_closures_creates_a_closure(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = client.post(
        planning.path("closures"),
        json={"first": "2026-12-24", "last": "2027-01-01", "label": "Fêtes de fin d'année"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "id": body["id"],
        "first": "2026-12-24",
        "last": "2027-01-01",
        "label": "Fêtes de fin d'année",
    }
    uuid.UUID(body["id"])


@pytest.mark.parametrize(
    "body",
    [
        {"first": "2026-11-14", "last": "2026-11-14"},
        {"first": "2026-11-14", "last": "2026-11-14", "label": None},
    ],
)
def test_post_api_closures_label_is_optional(
    client: Any, new_client: Callable[[], Any], body: dict[str, Any]
) -> None:
    planning = Planning(client, new_client)

    response = client.post(planning.path("closures"), json=body)

    assert response.status_code == 201
    assert response.json()["label"] is None


@pytest.mark.parametrize(
    "body",
    [
        {"last": "2026-11-14"},
        {"first": "2026-11-14"},
        {"first": "2026-11-15", "last": "2026-11-14"},
        {"first": "14/11/2026", "last": "2026-11-14"},
    ],
)
def test_post_api_closures_400_when_a_field_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, str]
) -> None:
    planning = Planning(client, new_client)

    response = client.post(planning.path("closures"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


def test_post_api_closures_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.add_closure("2026-11-14", "2026-11-14")

    response = planning.bruno_client.post(
        planning.path("closures"), json={"first": "2026-12-24", "last": "2026-12-26"}
    )

    assert response.status_code == 403
    assert settings_lines(client, planning.slug, "Closures") == ["Sat 14 Nov 2026"]
