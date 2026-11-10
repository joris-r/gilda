from collections.abc import Callable
from typing import Any

import pytest

from tests.planning.conftest import Planning, create_association, sign_up

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
NOTE = "Always group my registrations in pairs."


# Signed-in member required


# /planning/operations/general/member /core/operations/general/signed-out
@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("GET", "absences", None),
        ("POST", "absences", {"first": "2026-11-09", "last": "2026-11-15"}),
        ("PUT", f"absences/{UNKNOWN_ID}", {"first": "2026-11-09", "last": "2026-11-15"}),
        ("DELETE", f"absences/{UNKNOWN_ID}", None),
        ("GET", "note", None),
        ("PUT", "note", {"text": NOTE}),
        ("GET", "member-absences", None),
        ("GET", "notes", None),
    ],
)
def test_absences_and_note_401_when_signed_out(
    client: Any, method: str, rest: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, f"/api/associations/{UNKNOWN_ID}/{rest}", json=body)

    assert response.status_code == 401
    assert "error" in response.json()


# /planning/operations/general/member /core/operations/general/unknown-association
@pytest.mark.parametrize(
    ("method", "rest", "body"),
    [
        ("GET", "absences", None),
        ("POST", "absences", {"first": "2026-11-09", "last": "2026-11-15"}),
        ("GET", "note", None),
        ("PUT", "note", {"text": NOTE}),
        ("GET", "member-absences", None),
        ("GET", "notes", None),
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


def add_absence(as_client: Any, planning: Planning, first: str, last: str) -> dict[str, Any]:
    response = as_client.post(planning.path("absences"), json={"first": first, "last": last})
    assert response.status_code == 201, response.text
    absence: dict[str, Any] = response.json()
    return absence


# /planning/operations/add-absence/added
def test_post_api_absences_creates_an_absence(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.post(
        planning.path("absences"), json={"first": "2026-11-09", "last": "2026-11-15"}
    )

    assert response.status_code == 201
    absence = response.json()
    assert absence == {"id": absence["id"], "first": "2026-11-09", "last": "2026-11-15"}
    assert planning.bruno_client.get(planning.path("absences")).json() == [absence]


# /planning/operations/add-absence/added /planning/model/absence/order
def test_an_absence_may_last_one_day(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    absence = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-09")

    assert absence["first"] == absence["last"] == "2026-11-09"


# /planning/operations/list-absences/listed
def test_get_api_absences_lists_them_by_first_date(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    later = add_absence(planning.bruno_client, planning, "2026-12-21", "2027-01-03")
    earlier = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")

    response = planning.bruno_client.get(planning.path("absences"))

    assert response.status_code == 200
    assert response.json() == [earlier, later]


# /planning/operations/list-absences/listed
def test_get_api_absences_lists_past_ones_too(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    past = add_absence(planning.bruno_client, planning, "2020-01-06", "2020-01-10")

    assert planning.bruno_client.get(planning.path("absences")).json() == [past]


# /planning/operations/list-absences/listed
def test_get_api_absences_lists_only_the_users_own(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    brunos = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")
    chloes = add_absence(planning.chloe_client, planning, "2026-11-16", "2026-11-22")

    assert planning.bruno_client.get(planning.path("absences")).json() == [brunos]
    assert planning.chloe_client.get(planning.path("absences")).json() == [chloes]
    assert client.get(planning.path("absences")).json() == []


# /planning/operations/list-absences/listed
def test_absences_are_kept_per_association(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    add_absence(client, planning, "2026-11-09", "2026-11-15")

    response = client.get(f"/api/associations/{other['id']}/absences")

    assert response.status_code == 200
    assert response.json() == []


# /planning/operations/edit-absence/edited
def test_put_api_absence_edits_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    absence = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")

    response = planning.bruno_client.put(
        planning.path(f"absences/{absence['id']}"),
        json={"first": "2026-11-10", "last": "2026-11-20"},
    )

    assert response.status_code == 200
    edited = {"id": absence["id"], "first": "2026-11-10", "last": "2026-11-20"}
    assert response.json() == edited
    assert planning.bruno_client.get(planning.path("absences")).json() == [edited]


# /planning/operations/delete-absence/deleted
def test_delete_api_absence_removes_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    absence = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")

    response = planning.bruno_client.delete(planning.path(f"absences/{absence['id']}"))

    assert response.status_code == 204
    assert planning.bruno_client.get(planning.path("absences")).json() == []


# /planning/operations/edit-absence/unknown /planning/operations/delete-absence/unknown
@pytest.mark.parametrize("who", ["manager", "volunteer"])
def test_absence_404_when_not_the_users(
    client: Any, new_client: Callable[[], Any], who: str
) -> None:
    planning = Planning(client, new_client)
    absence = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")
    other = client if who == "manager" else planning.chloe_client
    at = planning.path(f"absences/{absence['id']}")

    edited = other.put(at, json={"first": "2026-11-10", "last": "2026-11-20"})
    deleted = other.delete(at)

    assert edited.status_code == 404
    assert deleted.status_code == 404
    assert planning.bruno_client.get(planning.path("absences")).json() == [absence]


# /planning/operations/edit-absence/unknown /planning/operations/delete-absence/unknown
def test_absence_404_when_of_another_association(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    absence = add_absence(client, planning, "2026-11-09", "2026-11-15")
    at = f"/api/associations/{other['id']}/absences/{absence['id']}"

    assert client.put(at, json={"first": "2026-11-10", "last": "2026-11-20"}).status_code == 404
    assert client.delete(at).status_code == 404


# /planning/operations/edit-absence/unknown /planning/operations/delete-absence/unknown
def test_absence_404_when_unknown(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    at = planning.path(f"absences/{UNKNOWN_ID}")

    assert client.put(at, json={"first": "2026-11-10", "last": "2026-11-20"}).status_code == 404
    assert client.delete(at).status_code == 404


INVALID_DATES = [
    {"last": "2026-11-15"},
    {"first": "2026-11-09"},
    {"first": "2026-11-16", "last": "2026-11-15"},
    {"first": "09/11/2026", "last": "2026-11-15"},
]


# /core/operations/general/malformed /planning/operations/add-absence/order
@pytest.mark.parametrize("body", INVALID_DATES)
def test_post_api_absences_400_when_a_field_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, str]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.post(planning.path("absences"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# /core/operations/general/malformed /planning/operations/edit-absence/order
@pytest.mark.parametrize("body", INVALID_DATES)
def test_put_api_absence_400_when_a_field_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, str]
) -> None:
    planning = Planning(client, new_client)
    absence = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")

    response = planning.bruno_client.put(planning.path(f"absences/{absence['id']}"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# Note


# /planning/operations/get-note/note
def test_get_api_note_is_empty_when_never_set(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.get(planning.path("note"))

    assert response.status_code == 200
    assert response.json() == {"text": ""}


# /planning/operations/set-note/set
def test_put_api_note_sets_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    assert response.status_code == 200
    assert response.json() == {"text": NOTE}
    assert planning.bruno_client.get(planning.path("note")).json() == {"text": NOTE}


# /planning/operations/set-note/set /planning/model/note/single
def test_put_api_note_replaces_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = planning.bruno_client.put(planning.path("note"), json={"text": "Mornings\nonly."})

    assert response.status_code == 200
    assert planning.bruno_client.get(planning.path("note")).json() == {"text": "Mornings\nonly."}


# /planning/operations/set-note/set
def test_put_api_note_empties_it(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = planning.bruno_client.put(planning.path("note"), json={"text": ""})

    assert response.status_code == 200
    assert planning.bruno_client.get(planning.path("note")).json() == {"text": ""}


# /planning/operations/get-note/note /planning/operations/set-note/set
def test_note_is_the_users_own(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    assert planning.chloe_client.get(planning.path("note")).json() == {"text": ""}
    assert client.get(planning.path("note")).json() == {"text": ""}


# /planning/operations/get-note/note
def test_note_is_kept_per_association(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    client.put(planning.path("note"), json={"text": NOTE})

    assert client.get(f"/api/associations/{other['id']}/note").json() == {"text": ""}


# /core/operations/general/malformed
@pytest.mark.parametrize("body", [{}, {"text": None}, {"text": 3}])
def test_put_api_note_400_when_text_is_missing_or_invalid(
    client: Any, new_client: Callable[[], Any], body: dict[str, Any]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.put(planning.path("note"), json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# GET /api/associations/{id}/member-absences


# /planning/operations/list-member-absences/listed
def test_get_api_member_absences_lists_all_members_by_first_date(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    chloes = add_absence(planning.chloe_client, planning, "2026-12-21", "2027-01-03")
    brunos = add_absence(planning.bruno_client, planning, "2026-11-09", "2026-11-15")
    alices = add_absence(client, planning, "2026-11-30", "2026-11-30")

    response = client.get(planning.path("member-absences"))

    assert response.status_code == 200
    assert response.json() == [
        {**brunos, "user_id": planning.bruno["id"]},
        {**alices, "user_id": planning.alice["id"]},
        {**chloes, "user_id": planning.chloe["id"]},
    ]


# /planning/operations/list-member-absences/listed
def test_get_api_member_absences_lists_past_ones_too(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    past = add_absence(planning.bruno_client, planning, "2020-01-06", "2020-01-10")

    response = client.get(planning.path("member-absences"))

    assert response.json() == [{**past, "user_id": planning.bruno["id"]}]


# /planning/operations/list-member-absences/listed
def test_get_api_member_absences_is_per_association(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    add_absence(client, planning, "2026-11-09", "2026-11-15")

    response = client.get(f"/api/associations/{other['id']}/member-absences")

    assert response.status_code == 200
    assert response.json() == []


# /planning/operations/list-member-absences/volunteer
def test_get_api_member_absences_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.get(planning.path("member-absences"))

    assert response.status_code == 403
    assert "error" in response.json()


# GET /api/associations/{id}/notes


# /planning/operations/list-notes/listed
def test_get_api_notes_one_entry_per_member(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    planning.bruno_client.put(planning.path("note"), json={"text": NOTE})

    response = client.get(planning.path("notes"))

    assert response.status_code == 200
    by_user = {entry["user_id"]: entry["text"] for entry in response.json()}
    assert len(response.json()) == 3
    assert by_user == {
        planning.alice["id"]: "",
        planning.bruno["id"]: NOTE,
        planning.chloe["id"]: "",
    }


# /planning/operations/list-notes/listed
def test_get_api_notes_is_per_association(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    client.put(planning.path("note"), json={"text": NOTE})

    response = client.get(f"/api/associations/{other['id']}/notes")

    assert response.json() == [{"user_id": planning.alice["id"], "text": ""}]


# /planning/operations/list-notes/volunteer
def test_get_api_notes_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    planning = Planning(client, new_client)

    response = planning.bruno_client.get(planning.path("notes"))

    assert response.status_code == 403
    assert "error" in response.json()
