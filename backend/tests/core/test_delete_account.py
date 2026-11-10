import re
import time
from collections.abc import Callable
from typing import Any

from tests.core.conftest import (
    PASSWORD,
    add_member,
    create_association,
    email_count,
    latest_email,
    latest_reset_token,
    latest_verification_token,
    sign_up,
    unique_email,
)


def delete_account(client: Any) -> Any:
    return client.delete("/api/accounts/me")


def access_token(client: Any, email: str) -> str:
    assert client.post("/api/access-link", json={"email": email}).status_code == 204
    match = re.search(r"/access\?token=([\w-]+)", latest_email(email)["Text"])
    assert match
    return match.group(1)


def roles(client: Any, association_id: str) -> dict[str, str]:
    members = client.get(f"/api/associations/{association_id}").json()["members"]
    return {m["display_name"]: m["role"] for m in members}


# DELETE /api/accounts/me


# /core/operations/delete-account/deleted
def test_delete_api_accounts_me_204(client: Any) -> None:
    sign_up(client, "Alice")

    response = delete_account(client)

    assert response.status_code == 204


# /core/operations/general/signed-out
def test_delete_api_accounts_me_401_when_signed_out(client: Any) -> None:
    response = delete_account(client)

    assert response.status_code == 401
    assert "error" in response.json()


# /core/operations/delete-account/deleted
def test_signs_out_every_session_of_the_user(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    other = new_client()
    assert (
        other.post("/api/session", json={"email": email, "password": PASSWORD}).status_code == 200
    )

    delete_account(client)

    assert client.get("/api/session").status_code == 401
    assert other.get("/api/session").status_code == 401


# /core/operations/delete-account/deleted
def test_the_password_no_longer_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    delete_account(client)

    response = new_client().post("/api/session", json={"email": email, "password": PASSWORD})
    assert response.status_code == 401


# /core/operations/delete-account/deleted
def test_the_access_link_no_longer_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    token = access_token(client, email)

    delete_account(client)

    response = new_client().post("/api/session/access-link", json={"token": token})
    assert response.status_code == 404


# /core/operations/delete-account/deleted
def test_a_pending_password_reset_no_longer_works(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    assert client.post("/api/accounts/password-reset", json={"email": email}).status_code == 204
    token = latest_reset_token(email)

    delete_account(client)

    response = new_client().post(
        "/api/accounts/password-reset/confirm", json={"token": token, "password": "battery staple"}
    )
    assert response.status_code == 404


# /core/operations/delete-account/deleted
def test_no_email_is_sent_to_the_erased_email_anymore(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    delete_account(client)
    before = email_count(email)

    other = new_client()
    assert other.post("/api/access-link", json={"email": email}).status_code == 204
    assert other.post("/api/accounts/password-reset", json={"email": email}).status_code == 204

    time.sleep(0.5)
    assert email_count(email) == before


# /core/operations/delete-account/deleted /core/operations/create-account/created
def test_the_email_can_be_used_by_a_new_account(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    old = sign_up(client, "Alice", email)
    delete_account(client)

    again = new_client()
    response = again.post(
        "/api/accounts",
        json={"display_name": "Alice B.", "email": email, "password": PASSWORD},
    )

    assert response.status_code == 201
    assert response.json()["id"] != old["id"]
    token = latest_verification_token(email)
    assert again.post("/api/accounts/verify", json={"token": token}).status_code == 200
    signed_in = again.post("/api/session", json={"email": email, "password": PASSWORD})
    assert signed_in.status_code == 200
    assert signed_in.json()["display_name"] == "Alice B."


# /core/operations/delete-account/deleted /core/operations/add-member/new-user
def test_the_email_can_be_added_as_a_new_member(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Bruno")
    bruno = new_client()
    old = sign_up(bruno, "Bruno", email)
    delete_account(bruno)
    sign_up(client, "Alice")
    association = create_association(client)

    response = add_member(client, association["id"], "Bruno B.", email)

    assert response.status_code == 201
    assert response.json()["user_id"] != old["id"]
    assert response.json()["display_name"] == "Bruno B."
    assert response.json()["has_account"] is False


# /core/operations/delete-account/deleted
def test_ends_every_membership(client: Any, new_client: Callable[[], Any]) -> None:
    sign_up(client, "Alice")
    first = create_association(client, "Jardin partagé des Lilas")
    second = create_association(client, "Repair Café Belleville")
    bruno = new_client()
    email = unique_email("Bruno")
    sign_up(bruno, "Bruno", email)
    add_member(client, first["id"], "Bruno", email)
    add_member(client, second["id"], "Bruno", email, "manager")

    delete_account(bruno)

    assert roles(client, first["id"]) == {"Alice": "manager"}
    assert roles(client, second["id"]) == {"Alice": "manager"}


# /core/operations/delete-account/last-manager
def test_the_remaining_members_become_managers_when_the_only_manager_leaves(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    sign_up(bruno, "Bruno", bruno_email)
    add_member(client, association["id"], "Bruno", bruno_email)
    add_member(client, association["id"], "Chloé", unique_email("Chloe"))

    assert delete_account(client).status_code == 204

    assert roles(bruno, association["id"]) == {"Bruno": "manager", "Chloé": "manager"}
    assert bruno.get(f"/api/associations/{association['id']}").json()["role"] == "manager"


# /core/operations/delete-account/last-manager
def test_roles_are_kept_when_another_manager_remains(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    zoe = new_client()
    zoe_email = unique_email("Zoe")
    sign_up(zoe, "Zoé", zoe_email)
    add_member(client, association["id"], "Zoé", zoe_email, "manager")
    add_member(client, association["id"], "Chloé", unique_email("Chloe"))

    delete_account(client)

    assert roles(zoe, association["id"]) == {"Zoé": "manager", "Chloé": "volunteer"}


# /core/operations/delete-account/last-manager
def test_the_only_member_of_an_association_can_delete_their_account(client: Any) -> None:
    sign_up(client, "Alice")
    create_association(client)

    assert delete_account(client).status_code == 204
