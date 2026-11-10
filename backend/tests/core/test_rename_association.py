from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    create_association,
    email_count,
    sign_up,
    unique_email,
)

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
OLD_NAME = "Jardin partagé des Lilas"
NEW_NAME = "Jardin des Lilas"


def manager_and_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> tuple[dict[str, Any], Any, dict[str, Any], str]:
    """Alice manages an association; Bruno, signed in on his own client, volunteers in it."""
    sign_up(client, "Alice")
    association = create_association(client, OLD_NAME)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    bruno_user = sign_up(bruno, "Bruno", bruno_email)
    assert add_member(client, association["id"], "Bruno", bruno_email).status_code == 201
    return association, bruno, bruno_user, bruno_email


# PATCH /api/associations/{id}


# /core/operations/general/signed-out
def test_patch_api_association_401_when_signed_out(client: Any) -> None:
    response = client.patch(f"/api/associations/{UNKNOWN_ID}", json={"name": NEW_NAME})

    assert response.status_code == 401
    assert "error" in response.json()


# /core/operations/update-association/renamed /core/operations/update-association/answer
def test_patch_api_association_renames_it(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, OLD_NAME)

    response = client.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 200
    assert response.json() == {
        "id": association["id"],
        "name": NEW_NAME,
        "slug": association["slug"],
        "role": "manager",
    }
    assert client.get(f"/api/associations/{association['id']}").json()["name"] == NEW_NAME
    assert [a["name"] for a in client.get("/api/associations").json()] == [NEW_NAME]


# /core/operations/update-association/renamed
def test_patch_api_association_keeps_its_members(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, bruno_user, _ = manager_and_volunteer(client, new_client)
    before = client.get(f"/api/associations/{association['id']}").json()["members"]

    response = client.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 200
    assert client.get(f"/api/associations/{association['id']}").json()["members"] == before
    assert bruno_user["id"] in [m["user_id"] for m in before]
    assert [a["name"] for a in bruno.get("/api/associations").json()] == [NEW_NAME]


# /core/operations/update-association/renamed
def test_patch_api_association_by_any_manager(client: Any, new_client: Callable[[], Any]) -> None:
    association, bruno, bruno_user, _ = manager_and_volunteer(client, new_client)
    promoted = client.patch(
        f"/api/associations/{association['id']}/members/{bruno_user['id']}",
        json={"role": "manager"},
    )
    assert promoted.status_code == 200

    response = bruno.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 200
    assert client.get(f"/api/associations/{association['id']}").json()["name"] == NEW_NAME


# /core/operations/update-association/volunteer
def test_patch_api_association_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _, _ = manager_and_volunteer(client, new_client)

    response = bruno.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 403
    assert "error" in response.json()
    assert client.get(f"/api/associations/{association['id']}").json()["name"] == OLD_NAME


# /core/operations/general/unknown-association
def test_patch_api_association_404_when_it_does_not_exist(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.patch(f"/api/associations/{UNKNOWN_ID}", json={"name": NEW_NAME})

    assert response.status_code == 404
    assert "error" in response.json()


# /core/operations/general/unknown-association
def test_patch_api_association_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client, OLD_NAME)
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))

    response = other.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 404
    assert "error" in response.json()
    assert client.get(f"/api/associations/{association['id']}").json()["name"] == OLD_NAME


# /core/operations/general/malformed /core/model/association/name
# /core/operations/update-association/neither /core/operations/general/refused
@pytest.mark.parametrize("body", [{}, {"name": ""}])
def test_patch_api_association_400_when_the_name_is_missing_or_empty(
    client: Any, body: dict[str, str]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client, OLD_NAME)

    response = client.patch(f"/api/associations/{association['id']}", json=body)

    assert response.status_code == 400
    assert "error" in response.json()
    assert client.get(f"/api/associations/{association['id']}").json()["name"] == OLD_NAME


# /core/operations/update-association/renamed
def test_patch_api_association_accepts_the_name_of_another_association(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client, OLD_NAME)
    create_association(client, NEW_NAME)

    response = client.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 200
    assert [a["name"] for a in client.get("/api/associations").json()] == [NEW_NAME, NEW_NAME]


# /core/operations/update-association/silent
def test_patch_api_association_members_are_not_told(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, _, _, bruno_email = manager_and_volunteer(client, new_client)
    before = email_count(bruno_email)

    response = client.patch(f"/api/associations/{association['id']}", json={"name": NEW_NAME})

    assert response.status_code == 200
    assert email_count(bruno_email) == before
