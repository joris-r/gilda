from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import (
    Planning,
    add_absence,
    availability_lines,
    create_association,
    notes_offered,
    sign_up,
)

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
NOTE = "Always group my registrations in pairs."


# Signed-in member required


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("POST", "absences", {"first": "2026-11-09", "last": "2026-11-15"}),
        ("PUT", "note", {"text": NOTE}),
    ],
)
def test_absences_and_note_401_when_signed_out(
    client: Any, method: str, rest: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, f"/api/associations/{UNKNOWN_ID}/{rest}", json=body)

    assert response.status_code == 401
    assert "error" in response.json()


@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("POST", "absences", {"first": "2026-11-09", "last": "2026-11-15"}),
        ("PUT", "note", {"text": NOTE}),
    ],
)
def test_absences_and_note_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any], method: str, rest: str, body: dict[str, Any] | None
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé")

    response = other.request(method, f"/api/associations/{association['id']}/{rest}", json=body)

    assert response.status_code == 404
    assert "error" in response.json()


# Absences


NOV = "Mon 9 Nov 2037 – Sun 15 Nov 2037"  # noqa: RUF001


def brunos_absences(planning: Planning) -> list[str]:
    """The absences Bruno's My availability lists."""
    return availability_lines(planning.bruno_client, planning.slug, "Absences")


def test_post_api_absences_creates_an_absence_of_the_users_own(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.post(
        planning.path("absences"), json={"first": "2037-11-09", "last": "2037-11-15"}
    )

    assert response.status_code == 201
    absence = response.json()
    assert absence == {"id": absence["id"], "first": "2037-11-09", "last": "2037-11-15"}
    assert brunos_absences(planning) == [NOV]
    assert availability_lines(client, planning.slug, "Absences") == []


def test_an_absence_may_last_one_day(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    absence = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-09")

    assert absence["first"] == absence["last"] == "2026-11-09"


def test_absences_are_kept_per_association(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    add_absence(client, planning, "2037-11-09", "2037-11-15")

    assert availability_lines(client, other["slug"], "Absences") == []


@pytest.mark.parametrize(
    "body",
    [
        {"last": "2026-11-15"},
        {"first": "2026-11-09"},
        {"first": "2026-11-16", "last": "2026-11-15"},
        {"first": "09/11/2026", "last": "2026-11-15"},
    ],
)
def test_post_api_absences_400_when_a_field_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, str]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.post(planning.path("absences"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


class TestAbsenceEndpointsRemoved:
    def test_get_api_absences_lists_nothing(
        self, client: Any, new_client: Callable[[], Any]
    ) -> None:
        planning = Planning(client, new_client)
        add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")

        response = planning.bruno_client.get(planning.path("absences"))

        assert response.status_code in (404, 405)

    @pytest.mark.parametrize(
        ("method", "body"),
        [("PUT", {"first": "2026-11-10", "last": "2026-11-20"}), ("DELETE", None)],
    )
    def test_put_and_delete_api_absence_change_nothing(
        self, client: Any, new_client: Callable[[], Any], method: str, body: dict[str, Any] | None
    ) -> None:
        planning = Planning(client, new_client)
        absence = add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")

        response = planning.bruno_client.request(
            method, planning.path(f"absences/{absence['id']}"), json=body
        )

        assert response.status_code in (404, 405)
        assert brunos_absences(planning) == [NOV]


# Note


def test_put_api_note_sets_the_users_own(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    assert response.status_code == 200
    assert response.json() == {"text": NOTE}
    assert notes_offered(planning) == {
        planning.alice["id"]: "",
        planning.bruno["id"]: NOTE,
        planning.chloe["id"]: "",
    }


def test_put_api_note_replaces_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = planning.bruno_client.put(planning.path("note"), json={"text": "Mornings\nonly."})

    assert response.status_code == 200
    assert notes_offered(planning)[planning.bruno["id"]] == "Mornings\nonly."


def test_put_api_note_empties_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = planning.bruno_client.put(planning.path("note"), json={"text": ""})

    assert response.status_code == 200
    assert notes_offered(planning)[planning.bruno["id"]] == ""


@pytest.mark.parametrize("body", [{}, {"text": None}, {"text": 3}])
def test_put_api_note_400_when_text_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, Any]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.put(planning.path("note"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


def test_get_api_note_leaves(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = planning.bruno_client.get(planning.path("note"))

    assert response.status_code in (404, 405)


@pytest.mark.parametrize("rest", ["member-absences", "notes", "registration-counts"])
def test_get_api_member_absences_notes_and_registration_counts_leave(
    client: Any, new_client: Callable[[], Any], rest: str
) -> None:
    planning = Planning(client, new_client)
    add_absence(planning.bruno_client, planning, "2037-11-09", "2037-11-15")
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = client.get(planning.path(rest))

    assert response.status_code in (404, 405)
