import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


# Signed-in member required


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("GET", "slots", None),
        ("POST", "slots", {"weekday": "thursday", "start": "10:00", "end": "13:00"}),
        ("DELETE", f"slots/{UNKNOWN_ID}", None),
        ("GET", "closures", None),
        ("POST", "closures", {"first": "2026-12-24", "last": "2026-12-26", "label": None}),
        ("DELETE", f"closures/{UNKNOWN_ID}", None),
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
        ("GET", "slots", None),
        ("POST", "slots", {"weekday": "thursday", "start": "10:00", "end": "13:00"}),
        ("GET", "closures", None),
        ("POST", "closures", {"first": "2026-12-24", "last": "2026-12-26", "label": None}),
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


def test_get_api_slots_lists_them_by_weekday_then_start(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_slot("saturday", "10:00", "13:00")
    planning.add_slot("thursday", "13:00", "16:00")
    planning.add_slot("thursday", "10:00", "13:00")

    response = planning.bruno_client.get(planning.path("slots"))

    assert response.status_code == 200
    assert [(s["weekday"], s["start"], s["end"]) for s in response.json()] == [
        ("thursday", "10:00", "13:00"),
        ("thursday", "13:00", "16:00"),
        ("saturday", "10:00", "13:00"),
    ]


def test_slots_are_kept_to_the_minute(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    slot = planning.add_slot("friday", "18:30", "20:15")

    assert (slot["start"], slot["end"]) == ("18:30", "20:15")


def test_delete_api_slot_removes_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")

    response = client.delete(planning.path(f"slots/{slot['id']}"))

    assert response.status_code == 204
    assert client.get(planning.path("slots")).json() == []


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


def test_slots_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    slot = planning.add_slot("thursday", "10:00", "13:00")
    bruno = planning.bruno_client

    created = bruno.post(
        planning.path("slots"), json={"weekday": "saturday", "start": "10:00", "end": "13:00"}
    )
    deleted = bruno.delete(planning.path(f"slots/{slot['id']}"))

    assert (created.status_code, deleted.status_code) == (403, 403)
    assert len(client.get(planning.path("slots")).json()) == 1


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


def test_get_api_closures_lists_them_by_first_date(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    planning.add_closure("2026-12-24", "2027-01-01", "Fêtes de fin d'année")
    planning.add_closure("2026-11-14", "2026-11-14", "Fête du quartier")

    response = planning.bruno_client.get(planning.path("closures"))

    assert response.status_code == 200
    assert [c["first"] for c in response.json()] == ["2026-11-14", "2026-12-24"]


def test_delete_api_closure_removes_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    closure = planning.add_closure("2026-11-14", "2026-11-14")

    response = client.delete(planning.path(f"closures/{closure['id']}"))

    assert response.status_code == 204
    assert client.get(planning.path("closures")).json() == []


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


def test_closures_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    closure = planning.add_closure("2026-11-14", "2026-11-14")
    bruno = planning.bruno_client

    created = bruno.post(
        planning.path("closures"), json={"first": "2026-12-24", "last": "2026-12-26"}
    )
    deleted = bruno.delete(planning.path(f"closures/{closure['id']}"))

    assert (created.status_code, deleted.status_code) == (403, 403)
    assert len(client.get(planning.path("closures")).json()) == 1
