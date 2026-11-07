import time
from collections.abc import Callable
from typing import Any

from tests.core.conftest import (
    add_member,
    ask_for_link,
    ask_for_reset,
    confirm_email,
    create_account,
    create_association,
    email_count,
    latest_access_token,
    latest_reset_token,
    latest_verification_token,
    member_line,
    members_roles,
    open_link,
    reset_password,
    shown,
    sign_in,
    sign_up,
    signed_in_as,
    unique_email,
    user_id_of,
)


def delete_account(client: Any) -> Any:
    """Confirms "Delete my account", as the dialog does."""
    return client.post("/delete-account")


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


def test_r29_signs_out_every_session_of_the_user(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    other = new_client()
    assert "window.location" in shown(sign_in(other, email))

    delete_account(client)

    assert signed_in_as(client) is None
    assert signed_in_as(other) is None


def test_r29_the_password_no_longer_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)

    delete_account(client)

    browser = new_client()
    assert "Wrong email or password." in shown(sign_in(browser, email))
    assert signed_in_as(browser) is None


def test_r29_the_access_link_no_longer_signs_in(client: Any, new_client: Callable[[], Any]) -> None:
    email = unique_email("Alice")
    sign_up(client, "Alice", email)
    assert ask_for_link(client, email).status_code == 200
    token = latest_access_token(email)

    delete_account(client)

    assert "This link is no longer valid." in shown(open_link(new_client(), token))


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
    assert ask_for_link(other, email).status_code == 200
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
    assert "window.location" in shown(sign_in(again, email))
    assert signed_in_as(again) == "Alice B."
    assert user_id_of(email) != old["id"]


def test_r29_the_email_can_be_added_as_a_new_member(
    client: Any, new_client: Callable[[], Any]
) -> None:
    email = unique_email("Bruno")
    bruno = new_client()
    old = sign_up(bruno, "Bruno", email)
    delete_account(bruno)
    sign_up(client, "Alice")
    association = create_association(client)

    added = add_member(client, association["slug"], "Bruno B.", email)

    assert added["user_id"] != old["id"]
    assert member_line(client, association["slug"], email).startswith(
        f"Bruno B. not joined yet {email} "
    )


def test_r29_ends_every_membership(client: Any, new_client: Callable[[], Any]) -> None:
    sign_up(client, "Alice")
    first = create_association(client, "Jardin partagé des Lilas")
    second = create_association(client, "Repair Café Belleville")
    bruno = new_client()
    email = unique_email("Bruno")
    sign_up(bruno, "Bruno", email)
    add_member(client, first["slug"], "Bruno", email)
    add_member(client, second["slug"], "Bruno", email, "manager")

    delete_account(bruno)

    assert members_roles(client, first["slug"]) == {"Alice": "manager"}
    assert members_roles(client, second["slug"]) == {"Alice": "manager"}


def test_r30_the_remaining_members_become_managers_when_the_only_manager_leaves(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    bruno = new_client()
    bruno_email = unique_email("Bruno")
    sign_up(bruno, "Bruno", bruno_email)
    add_member(client, association["slug"], "Bruno", bruno_email)
    add_member(client, association["slug"], "Chloé", unique_email("Chloe"))

    assert delete_account(client).status_code == 200

    assert members_roles(bruno, association["slug"]) == {"Bruno": "manager", "Chloé": "manager"}
    assert "Add a member" in bruno.get(f"/association/{association['slug']}/members").text


def test_r30_roles_are_kept_when_another_manager_remains(
    client: Any, new_client: Callable[[], Any]
) -> None:
    sign_up(client, "Alice")
    association = create_association(client)
    zoe = new_client()
    zoe_email = unique_email("Zoe")
    sign_up(zoe, "Zoé", zoe_email)
    add_member(client, association["slug"], "Zoé", zoe_email, "manager")
    add_member(client, association["slug"], "Chloé", unique_email("Chloe"))

    delete_account(client)

    assert members_roles(zoe, association["slug"]) == {"Zoé": "manager", "Chloé": "volunteer"}


def test_r30_the_only_member_of_an_association_can_delete_their_account(client: Any) -> None:
    sign_up(client, "Alice")
    create_association(client)

    assert delete_account(client).status_code == 200
