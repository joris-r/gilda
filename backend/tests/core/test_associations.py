import uuid
from collections.abc import Callable
from typing import Any

import pytest

from tests.core.conftest import (
    add_member,
    create_association,
    sign_up,
    unique_email,
)

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


def manager_and_volunteer(
    client: Any, new_client: Callable[[], Any]
) -> tuple[dict[str, Any], dict[str, Any], Any]:
    """Alice manages an association; Bruno, signed in on his own client, volunteers in it."""
    sign_up(client, "Alice")
    association = create_association(client)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    bruno_user = sign_up(bruno, "Bruno", bruno_email)
    assert add_member(client, association["id"], "Bruno", bruno_email).status_code == 201
    return association, bruno_user, bruno


# Signed-in user required


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/associations", None),
        ("POST", "/api/associations", {"name": "Repair Café"}),
        ("GET", f"/api/associations/{UNKNOWN_ID}", None),
        (
            "POST",
            f"/api/associations/{UNKNOWN_ID}/members",
            {"display_name": "Chloé", "email": "chloe@example.org", "role": "volunteer"},
        ),
        ("PATCH", f"/api/associations/{UNKNOWN_ID}/members/{UNKNOWN_ID}", {"role": "manager"}),
    ],
)
def test_associations_401_when_signed_out(
    client: Any, method: str, path: str, body: dict[str, str] | None
) -> None:
    response = client.request(method, path, json=body)

    assert response.status_code == 401
    assert "error" in response.json()


# POST /api/associations


def test_post_api_associations_makes_the_signed_in_user_its_manager(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.post("/api/associations", json={"name": "Repair Café Belleville"})

    assert response.status_code == 201
    body = response.json()
    assert body == {"id": body["id"], "name": "Repair Café Belleville", "role": "manager"}
    uuid.UUID(body["id"])


@pytest.mark.parametrize("body", [{}, {"name": ""}])
def test_post_api_associations_400_when_the_name_is_missing_or_empty(
    client: Any, body: dict[str, str]
) -> None:
    sign_up(client, "Alice")

    response = client.post("/api/associations", json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# GET /api/associations


def test_get_api_associations_lists_the_users_associations_with_their_role(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, _, bruno = manager_and_volunteer(client, new_client)
    own = create_association(bruno, "Repair Café Belleville")

    response = bruno.get("/api/associations")

    assert response.status_code == 200
    assert sorted(response.json(), key=lambda a: a["name"]) == [
        {"id": association["id"], "name": association["name"], "role": "volunteer"},
        {"id": own["id"], "name": "Repair Café Belleville", "role": "manager"},
    ]


def test_get_api_associations_omits_associations_of_others(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    create_association(client)
    other = new_client()
    sign_up(other, "Bruno")

    assert other.get("/api/associations").json() == []


# GET /api/associations/{id}


def test_get_api_association_shows_its_members(client: Any, new_client: Callable[[], Any]) -> None:
    alice_email = unique_email("Alice")
    alice = sign_up(client, "Alice", alice_email)
    association = create_association(client)
    chloe_email = unique_email("Chloe")
    chloe = add_member(client, association["id"], "Chloé", chloe_email).json()

    response = client.get(f"/api/associations/{association['id']}")

    assert response.status_code == 200
    body = response.json()
    assert {k: body[k] for k in ("id", "name", "timezone", "role")} == {
        "id": association["id"],
        "name": association["name"],
        "timezone": "Europe/Paris",
        "role": "manager",
    }
    assert sorted(body["members"], key=lambda m: m["display_name"]) == [
        {
            "user_id": alice["id"],
            "display_name": "Alice",
            "email": alice_email,
            "has_account": True,
            "email_verified": True,
            "role": "manager",
        },
        {
            "user_id": chloe["user_id"],
            "display_name": "Chloé",
            "email": chloe_email,
            "has_account": False,
            "email_verified": False,
            "role": "volunteer",
        },
    ]


def test_get_api_association_role_is_the_signed_in_users(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, _, bruno = manager_and_volunteer(client, new_client)

    assert bruno.get(f"/api/associations/{association['id']}").json()["role"] == "volunteer"


def test_get_api_association_404_when_it_does_not_exist(client: Any) -> None:
    sign_up(client, "Alice")

    response = client.get(f"/api/associations/{UNKNOWN_ID}")

    assert response.status_code == 404
    assert "error" in response.json()


def test_get_api_association_404_when_not_a_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    other = new_client()
    sign_up(other, "Bruno")

    response = other.get(f"/api/associations/{association['id']}")

    assert response.status_code == 404


# POST /api/associations/{id}/members


def test_post_api_members_creates_a_user_without_password(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    email = unique_email("Chloe")

    response = add_member(client, association["id"], "Chloé", email)

    assert response.status_code == 201
    body = response.json()
    assert body == {
        "user_id": body["user_id"],
        "display_name": "Chloé",
        "email": email,
        "has_account": False,
        "email_verified": False,
        "role": "volunteer",
    }
    uuid.UUID(body["user_id"])


def test_post_api_members_can_add_a_manager(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client)

    response = add_member(client, association["id"], "Bruno", unique_email("Bruno"), "manager")

    assert response.status_code == 201
    assert response.json()["role"] == "manager"


def test_r3_adding_an_existing_user_keeps_their_display_name(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    bruno_email = unique_email("Bruno")
    bruno = sign_up(new_client(), "Bruno", bruno_email)

    response = add_member(client, association["id"], "Someone else", bruno_email.upper())

    assert response.status_code == 201
    assert response.json() == {
        "user_id": bruno["id"],
        "display_name": "Bruno",
        "email": bruno_email,
        "has_account": True,
        "email_verified": True,
        "role": "volunteer",
    }


def test_r3_a_user_added_to_two_associations_is_one_user(client: Any) -> None:
    sign_up(client, "Alice")
    first = create_association(client, "Jardin partagé des Lilas")
    second = create_association(client, "Repair Café Belleville")
    email = unique_email("Chloe")

    in_first = add_member(client, first["id"], "Chloé", email).json()
    in_second = add_member(client, second["id"], "Chloé B.", email).json()

    assert in_second["user_id"] == in_first["user_id"]
    assert in_second["display_name"] == "Chloé"


def test_post_api_members_409_when_already_a_member(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    email = unique_email("Chloe")
    add_member(client, association["id"], "Chloé", email)

    response = add_member(client, association["id"], "Chloé", email, "manager")

    assert response.status_code == 409
    assert "error" in response.json()


def test_post_api_members_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    association, _, bruno = manager_and_volunteer(client, new_client)

    response = add_member(bruno, association["id"], "Chloé", unique_email("Chloe"))

    assert response.status_code == 403
    assert "error" in response.json()


@pytest.mark.parametrize(
    "body",
    [
        {"email": "missing-name@example.org", "role": "volunteer"},
        {"display_name": "", "email": "empty-name@example.org", "role": "volunteer"},
        {"display_name": "Chloé", "role": "volunteer"},
        {"display_name": "Chloé", "email": "not-an-email", "role": "volunteer"},
        {"display_name": "Chloé", "email": "bad-role@example.org", "role": "president"},
    ],
)
def test_post_api_members_400_when_a_field_is_missing_empty_or_invalid(
    client: Any, body: dict[str, str]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)

    response = client.post(f"/api/associations/{association['id']}/members", json=body)

    assert response.status_code == 400
    assert "error" in response.json()


# PATCH /api/associations/{id}/members/{user_id}


def test_patch_api_member_changes_the_role(client: Any, new_client: Callable[[], Any]) -> None:
    association, bruno_user, bruno = manager_and_volunteer(client, new_client)

    response = client.patch(
        f"/api/associations/{association['id']}/members/{bruno_user['id']}",
        json={"role": "manager"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "user_id": bruno_user["id"],
        "display_name": "Bruno",
        "email": bruno_user["email"],
        "has_account": True,
        "email_verified": True,
        "role": "manager",
    }
    assert bruno.get(f"/api/associations/{association['id']}").json()["role"] == "manager"


def test_r1_the_last_manager_cannot_be_demoted(client: Any) -> None:
    alice = sign_up(client, "Alice")
    association = create_association(client)

    response = client.patch(
        f"/api/associations/{association['id']}/members/{alice['id']}",
        json={"role": "volunteer"},
    )

    assert response.status_code == 409
    assert "error" in response.json()
    assert client.get(f"/api/associations/{association['id']}").json()["role"] == "manager"


def test_r1_a_manager_can_be_demoted_when_another_remains(
    client: Any, new_client: Callable[[], Any]
) -> None:
    alice = sign_up(client, "Alice")
    association = create_association(client)
    add_member(client, association["id"], "Bruno", unique_email("Bruno"), "manager")

    response = client.patch(
        f"/api/associations/{association['id']}/members/{alice['id']}",
        json={"role": "volunteer"},
    )

    assert response.status_code == 200
    assert response.json()["role"] == "volunteer"


def test_patch_api_member_404_when_the_user_is_not_a_member(client: Any) -> None:
    sign_up(client, "Alice")
    association = create_association(client)

    response = client.patch(
        f"/api/associations/{association['id']}/members/{UNKNOWN_ID}",
        json={"role": "manager"},
    )

    assert response.status_code == 404
    assert "error" in response.json()


def test_patch_api_member_403_for_a_volunteer(client: Any, new_client: Callable[[], Any]) -> None:
    association, bruno_user, bruno = manager_and_volunteer(client, new_client)

    response = bruno.patch(
        f"/api/associations/{association['id']}/members/{bruno_user['id']}",
        json={"role": "manager"},
    )

    assert response.status_code == 403
    assert "error" in response.json()


def test_patch_api_member_400_when_the_role_is_invalid(
    client: Any, new_client: Callable[[], Any]
) -> None:
    association, bruno_user, _ = manager_and_volunteer(client, new_client)

    response = client.patch(
        f"/api/associations/{association['id']}/members/{bruno_user['id']}",
        json={"role": "president"},
    )

    assert response.status_code == 400
    assert "error" in response.json()
