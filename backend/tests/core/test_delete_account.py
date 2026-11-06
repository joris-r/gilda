import re
import time
from collections.abc import Callable
from typing import Any

from tests.core.conftest import (
    PASSWORD,
    add_member,
    ask_for_reset,
    confirm_email,
    create_account,
    create_association,
    email_count,
    latest_email,
    latest_reset_token,
    latest_verification_token,
    reset_password,
    shown,
    sign_up,
    unique_email,
)


def delete_account(client: Any) -> Any:
    """Confirms "Delete my account", as the dialog does."""
    return client.post("/delete-account")


def access_token(client: Any, email: str) -> str:
    assert client.post("/api/access-link", json={"email": email}).status_code == 204
    match = re.search(r"/access\?token=([\w-]+)", latest_email(email)["Text"])
    assert match
    return match.group(1)


def roles(client: Any, association_id: str) -> dict[str, str]:
    members = client.get(f"/api/associations/{association_id}").json()["members"]
    return {m["display_name"]: m["role"] for m in members}


# Delete my account


def test_delete_my_account_leads_to_sign_in(client: Any) -> None:
    sign_up(client, "Alice")

    response = delete_account(client)

    assert "window.location" in shown(response)
    assert 'type="password"' in client.get("/").text


def test_delete_my_account_when_already_signed_out_leads_to_sign_in(client: Any) -> None:
    response = delete_account(client)

    assert "window.location" in shown(response)
    assert 'type="password"' in client.get("/").text


def test_delete_my_account_replaces_the_json_endpoint(client: Any) -> None:
    sign_up(client, "Alice")

    assert client.delete("/api/accounts/me").status_code == 404
    assert client.get("/api/session").status_code == 200


def test_r29_signs_out_every_session_of_the_user(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    other = new_client()
    assert (
        other.post("/api/session", json={"email": email, "password": PASSWORD}).status_code == 200
    )

    delete_account(client)

    assert client.get("/api/session").status_code == 401
    assert other.get("/api/session").status_code == 401


def test_r29_the_password_no_longer_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    delete_account(client)

    response = new_client().post("/api/session", json={"email": email, "password": PASSWORD})
    assert response.status_code == 401


def test_r29_the_access_link_no_longer_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    token = access_token(client, email)

    delete_account(client)

    response = new_client().post("/api/session/access-link", json={"token": token})
    assert response.status_code == 404


def test_r29_a_pending_password_reset_no_longer_works(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    ask_for_reset(client, email)
    token = latest_reset_token(email)

    delete_account(client)

    response = reset_password(new_client(), token, "battery staple")
    assert "This link is no longer valid." in shown(response)


def test_r29_no_email_is_sent_to_the_erased_email_anymore(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    delete_account(client)
    before = email_count(email)

    other = new_client()
    assert other.post("/api/access-link", json={"email": email}).status_code == 204
    assert ask_for_reset(other, email).status_code == 200

    time.sleep(0.5)
    assert email_count(email) == before


def test_r29_the_email_can_be_used_by_a_new_account(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    old = sign_up(client, "Alice", email)
    delete_account(client)

    again = new_client()
    create_account(again, "Alice B.", email)

    assert confirm_email(again, latest_verification_token(email)).status_code == 200
    signed_in = again.post("/api/session", json={"email": email, "password": PASSWORD})
    assert signed_in.status_code == 200
    assert signed_in.json()["display_name"] == "Alice B."
    assert signed_in.json()["id"] != old["id"]


def test_r29_the_email_can_be_added_as_a_new_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
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


def test_r29_ends_every_membership(client: Any, new_client: Callable[[], Any]) -> None:
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


def test_r30_the_remaining_members_become_managers_when_the_only_manager_leaves(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    sign_up(bruno, "Bruno", bruno_email)
    add_member(client, association["id"], "Bruno", bruno_email)
    add_member(client, association["id"], "Chloé", unique_email("Chloe"))

    assert delete_account(client).status_code == 200

    assert roles(bruno, association["id"]) == {"Bruno": "manager", "Chloé": "manager"}
    assert bruno.get(f"/api/associations/{association['id']}").json()["role"] == "manager"


def test_r30_roles_are_kept_when_another_manager_remains(
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


def test_r30_the_only_member_of_an_association_can_delete_their_account(client: Any) -> None:
    sign_up(client, "Alice")
    create_association(client)

    assert delete_account(client).status_code == 200
