from collections.abc import Callable
from typing import Any

from tests.core.conftest import (
    add_member,
    create_association,
    email_count,
    sign_up,
    unique_email,
)

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def manager_and_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> tuple[dict[str, Any], Any, dict[str, Any], str]:
    """Alice manages an association; Bruno, signed in on his own client, volunteers in it."""
    sign_up(client, "Alice")
    association = create_association(client)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    bruno_user = sign_up(bruno, "Bruno", bruno_email)
    assert add_member(client, association["id"], "Bruno", bruno_email).status_code == 201
    return association, bruno, bruno_user, bruno_email


# DELETE /api/associations/{id}


def test_delete_api_association_401_when_signed_out(client: Any) -> None:
    response = client.delete(f"/api/associations/{UNKNOWN_ID}")

    assert response.status_code == 401
    assert "error" in response.json()


def test_delete_api_association_deletes_it(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client)

    response = client.delete(f"/api/associations/{association['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/associations/{association['id']}").status_code == 404
    assert client.get("/api/associations").json() == []


def test_delete_api_association_by_any_manager(client: Any, new_client: Callable[[], Any]) -> None:
    association, bruno, bruno_user, _ = manager_and_volunteer(client, new_client)
    promoted = client.patch(
        f"/api/associations/{association['id']}/members/{bruno_user['id']}",
        json={"role": "manager"},
    )
    assert promoted.status_code == 200

    assert bruno.delete(f"/api/associations/{association['id']}").status_code == 204

    assert client.get(f"/api/associations/{association['id']}").status_code == 404


def test_delete_api_association_403_for_a_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _, _ = manager_and_volunteer(client, new_client)

    response = bruno.delete(f"/api/associations/{association['id']}")

    assert response.status_code == 403
    assert "error" in response.json()
    assert client.get(f"/api/associations/{association['id']}").status_code == 200


def test_delete_api_association_404_when_it_does_not_exist(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.delete(f"/api/associations/{UNKNOWN_ID}")

    assert response.status_code == 404
    assert "error" in response.json()


def test_delete_api_association_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Zoé", unique_email("Zoe"))

    response = other.delete(f"/api/associations/{association['id']}")

    assert response.status_code == 404
    assert "error" in response.json()
    assert client.get(f"/api/associations/{association['id']}").status_code == 200


# R34


def test_r34_members_stay_users_in_their_other_associations(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _, bruno_email = manager_and_volunteer(client, new_client)
    other = create_association(client, "Repair Café Belleville")
    assert add_member(client, other["id"], "Bruno", bruno_email).status_code == 201

    assert client.delete(f"/api/associations/{association['id']}").status_code == 204

    assert bruno.get("/api/session").status_code == 200
    assert [a["id"] for a in bruno.get("/api/associations").json()] == [other["id"]]
    assert client.get(f"/api/associations/{other['id']}").status_code == 200


def test_r34_a_member_left_in_no_association_stays_a_user(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno, _, _ = manager_and_volunteer(client, new_client)

    assert client.delete(f"/api/associations/{association['id']}").status_code == 204

    assert bruno.get("/api/session").status_code == 200
    assert bruno.get("/api/associations").json() == []


def test_r34_an_added_user_can_be_added_to_another_association_afterwards(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, _, bruno_user, bruno_email = manager_and_volunteer(client, new_client)
    assert client.delete(f"/api/associations/{association['id']}").status_code == 204

    other = create_association(client, "Repair Café Belleville")
    response = add_member(client, other["id"], "Bruno", bruno_email)

    assert response.status_code == 201
    assert response.json()["user_id"] == bruno_user["id"]


def test_r34_members_are_not_told(client: Any, new_client: Callable[[], Any]) -> None:
    association, _, _, bruno_email = manager_and_volunteer(client, new_client)
    before = email_count(bruno_email)

    assert client.delete(f"/api/associations/{association['id']}").status_code == 204

    assert email_count(bruno_email) == before
